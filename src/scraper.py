"""
Basketball-Reference Data Scraper
Collects player stats, game logs, and team data from Basketball-Reference.com

Learning Goals:
- Web scraping with BeautifulSoup
- Rate limiting and respectful scraping
- Data cleaning and validation
- Database insertion patterns
"""

import requests
from bs4 import BeautifulSoup
from io import StringIO
import pandas as pd
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
import re
from typing import Dict, List, Optional
import logging
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


class BasketballReferenceScraper:
    """
    Main scraper class for Basketball-Reference data.
    
    Important: Basketball-Reference requests that scrapers:
    - Use rate limiting (3 seconds between requests)
    - Include a User-Agent header
    - Don't overwhelm their servers
    """
    
    BASE_URL = "https://www.basketball-reference.com"
    
    def __init__(self):
        """Initialize scraper with database connection."""
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', '5432')
        )
        self.session = requests.Session()
        # Being a good internet citizen with User-Agent
        self.session.headers.update({
            'User-Agent': 'NBA-Parlay-Analyzer/1.0 (Educational Project)'
        })
    
    def _rate_limit(self):
        """Sleep to respect Basketball-Reference's rate limits."""
        time.sleep(3)  # 3 seconds between requests
    
    def scrape_player_season_stats(self, season: int = 2025) -> pd.DataFrame:
        """
        Scrape all player stats for a given season.
        
        Args:
            season: NBA season year (2025 means 2024-25 season)
        
        Returns:
            DataFrame with player stats
        """
        logger.info(f"Scraping player stats for {season-1}-{season} season")
        
        url = f"{self.BASE_URL}/leagues/NBA_{season}_per_game.html"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            self._rate_limit()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the stats table
            table = soup.find('table', {'id': 'per_game_stats'})
            
            if not table:
                logger.error(f"Could not find stats table for season {season}")
                return pd.DataFrame()
            
            # Extract data using pandas with StringIO
            from io import StringIO
            df = pd.read_html(StringIO(str(table)))[0]
            
            # Clean column names (pandas adds multi-level headers)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(-1)
            
            # Remove header rows that appear in the middle of data
            df = df[df['Player'] != 'Player']
            
            # Drop unnamed columns
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            
            # Add season column
            df['season'] = season
            
            logger.info(f"Successfully scraped {len(df)} player records")
            return df
            
        except Exception as e:
            logger.error(f"Error scraping player stats: {e}")
            return pd.DataFrame()
    
    def scrape_player_game_log(self, player_id: str, season: int = 2025) -> pd.DataFrame:
        """
        Scrape individual game logs for a specific player.
        
        Args:
            player_id: Basketball-Reference player ID (e.g., 'curryst01')
            season: NBA season
        
        Returns:
            DataFrame with game-by-game stats
        """
        logger.info(f"Scraping game log for player {player_id}, season {season}")
        
        url = f"{self.BASE_URL}/players/{player_id[0]}/{player_id}/gamelog/{season}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            self._rate_limit()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'pgl_basic'}) or soup.find('table', {'id': 'player_game_log_reg'})
            
            if not table:
                logger.warning(f"No game log found for {player_id}")
                return pd.DataFrame()
            
            # Use pandas to parse
            df = pd.read_html(StringIO(str(table)))[0]
            
            # Clean multi-level columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel()
            
            # Remove header rows
            df = df[df['Date'] != 'Date']
            
            # Add metadata
            df['player_id'] = player_id
            df['season'] = season
            
            logger.info(f"Scraped {len(df)} games for {player_id}")
            return df
            
        except Exception as e:
            logger.error(f"Error scraping game log for {player_id}: {e}")
            return pd.DataFrame()
    
    def clean_player_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize player stats data."""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Convert numeric columns
        numeric_cols = ['Age', 'G', 'GS', 'MP', 'FG', 'FGA', 'FG%', 
                       '3P', '3PA', '3P%', '2P', '2PA', '2P%',
                       'eFG%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB', 
                       'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean player names
        if 'Player' in df.columns:
            df['Player'] = df['Player'].str.strip()
        
        # Standardize team abbreviations
        team_mapping = {
            'CHO': 'CHA',
            'BRK': 'BKN',
            'PHO': 'PHX',
        }
        
        if 'Tm' in df.columns:
            df['Tm'] = df['Tm'].replace(team_mapping)
        
        return df
    
    def save_players_to_db(self, df: pd.DataFrame):
        """Insert player data into database."""
        if df.empty:
            logger.warning("No player data to insert")
            return
        
        cursor = self.conn.cursor()
        
        try:
            inserted = 0
            for _, row in df.iterrows():
                # Get team_id from database
                cursor.execute(
                    "SELECT id FROM teams WHERE abbreviation = %s",
                    (row.get('Tm'),)
                )
                team_result = cursor.fetchone()
                team_id = team_result[0] if team_result else None
                
                # Insert or update player
                cursor.execute("""
                    INSERT INTO players (name, team_id, position, is_active)
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (basketball_reference_id) 
                    DO UPDATE SET 
                        name = EXCLUDED.name,
                        team_id = EXCLUDED.team_id,
                        position = EXCLUDED.position
                    RETURNING id
                """, (
                    row.get('Player'),
                    team_id,
                    row.get('Pos')
                ))
                inserted += 1
            
            self.conn.commit()
            logger.info(f"✅ Successfully inserted/updated {inserted} players")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving players: {e}")
            raise
        finally:
            cursor.close()
    
    def get_team_id(self, team_abbr: str) -> Optional[int]:
        """Get team ID from abbreviation."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM teams WHERE abbreviation = %s",
            (team_abbr,)
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Test functions
def test_scrape_current_season():
    """Test scraping current season player stats."""
    scraper = BasketballReferenceScraper()
    
    try:
        # Scrape current season
        df = scraper.scrape_player_season_stats(season=2025)
        
        if not df.empty:
            # Clean data
            df_clean = scraper.clean_player_stats(df)
            
            # Save to CSV for inspection
            df_clean.to_csv('data/players_2024_25.csv', index=False)
            
            print(f"\n✅ Scraped {len(df_clean)} players")
            print(f"📁 Saved to data/players_2024_25.csv")
            print(f"\nTop 5 scorers:")
            top_scorers = df_clean.nlargest(5, 'PTS')[['Player', 'Team', 'PTS', 'AST', 'TRB']]
            print(top_scorers.to_string(index=False))
            
            return df_clean
        else:
            print("❌ No data scraped")
            
    finally:
        scraper.close()


def test_scrape_player_gamelog():
    """Test scraping a specific player's game log."""
    scraper = BasketballReferenceScraper()
    
    try:
        # Scrape Stephen Curry's game log
        df = scraper.scrape_player_game_log('curryst01', season=2025)
        
        if not df.empty:
            df.to_csv('data/curry_gamelog_2024_25.csv', index=False)
            
            print(f"\n✅ Scraped {len(df)} games for Stephen Curry")
            print(f"📁 Saved to data/curry_gamelog_2024_25.csv")
            
            # Show recent games
            print(f"\nLast 5 games:")
            recent = df.head(5)[['Date', 'Opp', 'PTS', 'AST', 'TRB']]
            print(recent.to_string(index=False))
            
        else:
            print("❌ No game log found")
            
    finally:
        scraper.close()


if __name__ == "__main__":
    print("🏀 Basketball-Reference Scraper Test\n")
    print("=" * 60)
    
    # Test 1: Current season stats
    print("\n📊 Test 1: Scraping current season player stats...")
    test_scrape_current_season()
    
    # Test 2: Player game log
    print("\n" + "=" * 60)
    print("\n📊 Test 2: Scraping Stephen Curry's game log...")
    test_scrape_player_gamelog()
    
    print("\n" + "=" * 60)
    print("✅ All tests complete!")