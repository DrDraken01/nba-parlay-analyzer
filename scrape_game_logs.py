"""
Scrape historical game logs for players
This will give us real variance data and rolling averages
"""

from src.scraper import BasketballReferenceScraper
import pandas as pd
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_top_players_gamelogs(season: int = 2024, min_ppg: float = 15.0):
    """
    Scrape game logs for top scorers from the season.
    
    Args:
        season: NBA season year
        min_ppg: Minimum PPG to include player
    """
    # Load current season stats to identify top players
    df = pd.read_csv('data/players_2024_25.csv')
    
    # Filter to top scorers/playmakers
    top_players = df[df['PTS'] >= min_ppg].copy()
    
    # Sort by points
    top_players = top_players.sort_values('PTS', ascending=False)
    
    logger.info(f"Found {len(top_players)} players averaging {min_ppg}+ PPG")
    
    # We need Basketball-Reference IDs
    # For MVP, we'll manually create a list of key players
    # In production, you'd scrape the player ID from their page
    
    key_players = {
        'Stephen Curry': 'curryst01',
        'LeBron James': 'jamesle01',
        'Giannis Antetokounmpo': 'antetgi01',
        'Nikola Jokić': 'jokicni01',
        'Luka Dončić': 'doncilu01',
        'Kevin Durant': 'duranke01',
        'Joel Embiid': 'embiijo01',
        'Damian Lillard': 'lillada01',
        'Jayson Tatum': 'tatumja01',
        'Shai Gilgeous-Alexander': 'gilgesh01',
        'Anthony Edwards': 'edwaran01',
        'Devin Booker': 'bookede01',
        'Donovan Mitchell': 'mitchdo01',
        'Anthony Davis': 'davisan02',
        'Kawhi Leonard': 'leonaka01',
        'Kyrie Irving': 'irvinky01',
        'Trae Young': 'youngtr01',
        'Ja Morant': 'moranja01',
        'Zion Williamson': 'willizi01',
        'Jimmy Butler': 'butleji01'
    }
    
    scraper = BasketballReferenceScraper()
    all_gamelogs = []
    
    try:
        for player_name, player_id in key_players.items():
            logger.info(f"Scraping {player_name}...")
            
            try:
                gamelog = scraper.scrape_player_game_log(player_id, season)
                
                if not gamelog.empty:
                    gamelog['player_name'] = player_name
                    all_gamelogs.append(gamelog)
                    logger.info(f"  ✓ Got {len(gamelog)} games")
                else:
                    logger.warning(f"  ✗ No data for {player_name}")
                
                time.sleep(3)  # Rate limiting
                
            except Exception as e:
                logger.error(f"  ✗ Error scraping {player_name}: {e}")
                continue
        
        # Combine all game logs
        if all_gamelogs:
            combined = pd.concat(all_gamelogs, ignore_index=True)
            
            # Save to CSV
            output_file = f'data/gamelogs_{season}.csv'
            combined.to_csv(output_file, index=False)
            
            logger.info(f"\n✓ Successfully scraped {len(all_gamelogs)} players")
            logger.info(f"✓ Total games: {len(combined)}")
            logger.info(f"✓ Saved to {output_file}")
            
            return combined
        else:
            logger.error("No game logs scraped")
            return pd.DataFrame()
            
    finally:
        scraper.close()


if __name__ == "__main__":
    print("Scraping Historical Game Logs\n" + "="*60)
    print("\nThis will take 2-3 minutes due to rate limiting...")
    print("Scraping 20 top players from 2023-24 season\n")
    
    df = scrape_top_players_gamelogs(season=2024, min_ppg=15.0)
    
    if not df.empty:
        print("\n" + "="*60)
        print("\nSample Data:")
        print(df.head())
        print(f"\nColumns: {df.columns.tolist()}")
    
    print("\n" + "="*60)
    print("Complete!")