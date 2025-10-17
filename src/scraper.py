"""
NBA Stats API Scraper
Gets game logs for all active NBA players (~450 players in 5-10 minutes)

Usage:
    python scraper.py
"""

import pandas as pd
from nba_api.stats.endpoints import playergamelog, commonallplayers
from nba_api.stats.static import teams
import time
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NBAGameLogScraper:
    """Scrapes game logs for all active NBA players."""
    
    CURRENT_SEASON = "2024-25"
    
    def __init__(self):
        """Initialize scraper."""
        self.all_teams = teams.get_teams()
        self.team_abbr_map = {team['id']: team['abbreviation'] for team in self.all_teams}
    
    def get_all_active_players(self):
        """
        Get all active NBA players from the official API.
        
        Returns:
            List of dicts with player id, name, team_id
        """
        logger.info("Fetching all active players from NBA API...")
        
        try:
            all_players_data = commonallplayers.CommonAllPlayers(
                season=self.CURRENT_SEASON,
                is_only_current_season=1
            ).get_data_frames()[0]
            
            active_players = all_players_data[all_players_data['ROSTERSTATUS'] == 1]
            
            players_list = []
            for _, player in active_players.iterrows():
                players_list.append({
                    'id': player['PERSON_ID'],
                    'name': player['DISPLAY_FIRST_LAST'],
                    'team_id': player['TEAM_ID']
                })
            
            logger.info(f"✅ Found {len(players_list)} active players")
            return players_list
            
        except Exception as e:
            logger.error(f"Error fetching players: {e}")
            return []
    
    def get_player_gamelog(self, player_id, player_name):
        """
        Get game log for a specific player.
        
        Args:
            player_id: NBA player ID
            player_name: Player's full name
            
        Returns:
            DataFrame with game logs
        """
        try:
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=self.CURRENT_SEASON
            )
            
            df = gamelog.get_data_frames()[0]
            
            if df.empty:
                return pd.DataFrame()
            
            df['player_name'] = player_name
            
            # Extract opponent - handle both "vs." and "@" formats
            # "LAL vs. BOS" -> "BOS", "LAL @ BOS" -> "BOS"
            df['Opp'] = df['MATCHUP'].apply(lambda x: 
                x.split('vs. ')[-1] if 'vs.' in str(x) 
                else x.split('@ ')[-1] if '@' in str(x) 
                else None
            )
            
            # Rename columns to match analyzer format
            df = df.rename(columns={
                'GAME_DATE': 'Date',
                'PTS': 'PTS',
                'AST': 'AST',
                'REB': 'TRB',
                'FG3M': '3P',
                'STL': 'STL',
                'BLK': 'BLK',
                'TOV': 'TOV',
                'MIN': 'MP'
            })
            
            # Keep only needed columns
            keep_cols = ['player_name', 'Date', 'Opp', 'PTS', 'AST', 'TRB', '3P', 'STL', 'BLK', 'TOV', 'MP']
            df = df[[col for col in keep_cols if col in df.columns]]
            
            return df
            
        except Exception as e:
            logger.error(f"  ❌ Error for {player_name}: {e}")
            return pd.DataFrame()
    
    def scrape_all(self, output_file='data/gamelogs_2024.csv'):
        """
        Main method: Scrape game logs for ALL active players.
        
        Args:
            output_file: Where to save the CSV (default: data/gamelogs_2024.csv)
        """
        logger.info("=" * 80)
        logger.info("🏀 NBA GAMELOG SCRAPER")
        logger.info("=" * 80)
        
        # Step 1: Get all active players
        all_players = self.get_all_active_players()
        
        if not all_players:
            logger.error("❌ Could not fetch players list")
            return
        
        logger.info(f"\n📊 Fetching game logs for {len(all_players)} players...")
        logger.info("⏱️ Estimated time: 5-10 minutes\n")
        
        all_gamelogs = []
        failed_players = []
        
        # Step 2: Get game logs for each player
        for i, player in enumerate(all_players, 1):
            logger.info(f"[{i}/{len(all_players)}] {player['name']}")
            
            try:
                gamelog = self.get_player_gamelog(player['id'], player['name'])
                
                if not gamelog.empty:
                    all_gamelogs.append(gamelog)
                    logger.info(f"  ✅ {len(gamelog)} games")
                else:
                    failed_players.append(player['name'])
                    logger.info(f"  ⚠️ No games found")
                
                # Rate limiting (be nice to NBA's servers)
                time.sleep(0.6)
                
                # Save progress every 100 players
                if i % 100 == 0:
                    self._save_progress(all_gamelogs, output_file)
                    logger.info(f"\n💾 Progress saved: {i}/{len(all_players)}\n")
                
            except Exception as e:
                logger.error(f"  ❌ Failed: {e}")
                failed_players.append(player['name'])
                time.sleep(2)  # Extra delay on error
        
        # Step 3: Combine and save final result
        if all_gamelogs:
            logger.info("\n✅ Combining and saving final data...")
            final_df = pd.concat(all_gamelogs, ignore_index=True)
            
            # Create data directory if it doesn't exist
            os.makedirs('data', exist_ok=True)
            
            # Save to CSV
            final_df.to_csv(output_file, index=False)
            
            # Print summary
            logger.info("=" * 80)
            logger.info("✅ SCRAPING COMPLETE!")
            logger.info("=" * 80)
            logger.info(f"📊 Total players attempted: {len(all_players)}")
            logger.info(f"✅ Successfully scraped: {len(all_gamelogs)}")
            logger.info(f"❌ Failed: {len(failed_players)}")
            logger.info(f"📁 Saved to: {output_file}")
            logger.info(f"📈 Total games: {len(final_df):,}")
            logger.info(f"👥 Unique players: {final_df['player_name'].nunique()}")
            
            # Show sample
            logger.info("\n📋 Sample of data:")
            print(final_df.head(5).to_string(index=False))
            
            if failed_players and len(failed_players) < 20:
                logger.info(f"\n⚠️ Players with no data: {', '.join(failed_players)}")
            
            # Verify key players
            self._verify_key_players(final_df)
            
        else:
            logger.error("❌ No data collected!")
    
    def _save_progress(self, gamelogs, output_file):
        """Save progress checkpoint to avoid losing data."""
        if gamelogs:
            temp_df = pd.concat(gamelogs, ignore_index=True)
            temp_file = output_file.replace('.csv', '_progress.csv')
            temp_df.to_csv(temp_file, index=False)
    
    def _verify_key_players(self, df):
        """Check if key players are in the data."""
        key_players = ['LeBron James', 'Anthony Edwards', 'Stephen Curry', 'Luka Doncic']
        
        logger.info("\n🔍 Verifying key players:")
        for player in key_players:
            if player in df['player_name'].values:
                games = len(df[df['player_name'] == player])
                logger.info(f"  ✅ {player}: {games} games")
            else:
                logger.info(f"  ❌ {player}: NOT FOUND")


def verify_existing_data(csv_file='data/gamelogs_2024.csv'):
    """
    Verify an existing scraped CSV file.
    
    Args:
        csv_file: Path to the CSV file to verify
    """
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        return
    
    df = pd.read_csv(csv_file)
    
    print("\n" + "=" * 60)
    print("📊 DATA VERIFICATION")
    print("=" * 60)
    print(f"Total rows: {len(df):,}")
    print(f"Unique players: {df['player_name'].nunique()}")
    print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"\nColumns: {', '.join(df.columns.tolist())}")
    
    print("\n📋 Top 10 players by games logged:")
    top_players = df['player_name'].value_counts().head(10)
    for player, games in top_players.items():
        print(f"  {player}: {games} games")
    
    print("\n✅ Sample data:")
    print(df.head(3).to_string(index=False))
    
    # Check for missing data
    missing = df.isnull().sum()
    if missing.any():
        print("\n⚠️ Missing values:")
        print(missing[missing > 0])
    else:
        print("\n✅ No missing values")
    
    print("\n" + "=" * 60)


def main():
    """Main function with menu."""
    print("\n🏀 NBA GAMELOG SCRAPER")
    print("=" * 60)
    print("1. Scrape all players (5-10 minutes)")
    print("2. Verify existing data")
    print("3. Exit")
    print("=" * 60)
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    if choice == '1':
        print("\n⚠️ This will scrape ~450 active NBA players")
        print("⏱️ Time required: 5-10 minutes")
        confirm = input("Proceed? (yes/no): ").lower()
        
        if confirm in ['yes', 'y']:
            scraper = NBAGameLogScraper()
            scraper.scrape_all()
            
            print("\n✅ Scraping complete! Verifying data...\n")
            verify_existing_data()
        else:
            print("Cancelled.")
    
    elif choice == '2':
        verify_existing_data()
    
    elif choice == '3':
        print("Goodbye!")
    
    else:
        print("❌ Invalid choice!")


if __name__ == "__main__":
    # Check if nba-api is installed
    try:
        import nba_api
    except ImportError:
        print("\n❌ NBA API package not installed!")
        print("Install it with: pip install nba-api")
        print("\nThen run this script again.")
        exit(1)
    
    main()