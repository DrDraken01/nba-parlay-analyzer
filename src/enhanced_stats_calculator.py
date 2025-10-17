"""
Enhanced Stats Calculator with Real Variance from Game Logs
Uses historical game data for accurate probability calculations
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedStatsCalculator:
    """Calculate stats using real game log data."""
    
    def __init__(self, gamelog_file: str = 'data/gamelogs_2024.csv'):
        """
        Initialize with game log data.
        
        Args:
            gamelog_file: Path to CSV with game logs
        """
        try:
            self.gamelogs = pd.read_csv(gamelog_file)
            
            # Clean numeric columns - filter out 'Inactive' rows first
            self.gamelogs = self.gamelogs[self.gamelogs['PTS'] != 'Inactive']
            self.gamelogs = self.gamelogs[self.gamelogs['PTS'] != 'Did Not Play']
            self.gamelogs = self.gamelogs[self.gamelogs['PTS'] != 'Did Not Dress']
            
            # Remove summary/total rows (they have NaN dates)
            self.gamelogs = self.gamelogs[self.gamelogs['Date'].notna()]

            # Now convert to numeric - include TOV (turnovers)
            numeric_cols = ['PTS', 'AST', 'TRB', '3P', 'STL', 'BLK', 'TOV', 'MP']
            for col in numeric_cols:
                if col in self.gamelogs.columns:
                    self.gamelogs[col] = pd.to_numeric(self.gamelogs[col], errors='coerce')
            
            # Drop any remaining NaN rows
            self.gamelogs = self.gamelogs.dropna(subset=['PTS'])
            
            logger.info(f"Loaded {len(self.gamelogs)} games for {self.gamelogs['player_name'].nunique()} players")
        except Exception as e:
            logger.error(f"Error loading game logs: {e}")
            self.gamelogs = pd.DataFrame()
    
    def get_player_stats(self, player_name: str, last_n_games: Optional[int] = None) -> Dict:
        """
        Get player statistics with real variance.
        
        Args:
            player_name: Player's full name
            last_n_games: If specified, only use last N games (for recent form)
            
        Returns:
            Dict with mean, std, and other stats
        """
        player_games = self.gamelogs[self.gamelogs['player_name'] == player_name].copy()
        
        if player_games.empty:
            logger.warning(f"No game log data for {player_name}")
            return {}
        
        # Sort by date (most recent first) and limit if requested
        player_games = player_games.sort_values('Date', ascending=False)
        if last_n_games:
            player_games = player_games.head(last_n_games)
        
        stats = {
            'player': player_name,
            'games_analyzed': len(player_games),
            'timeframe': f'Last {last_n_games} games' if last_n_games else 'Full season'
        }
        
        # Calculate mean and std for each stat (including TOV now)
        for stat in ['PTS', 'AST', 'TRB', '3P', 'STL', 'BLK', 'TOV']:
            if stat in player_games.columns:
                values = player_games[stat].dropna()
                if len(values) > 0:
                    stats[f'{stat.lower()}_mean'] = round(values.mean(), 2)
                    stats[f'{stat.lower()}_std'] = round(values.std(), 2)
                    stats[f'{stat.lower()}_min'] = int(values.min())
                    stats[f'{stat.lower()}_max'] = int(values.max())
        
        # Calculate combo stats
        if 'PTS' in player_games.columns and 'AST' in player_games.columns:
            pa = player_games['PTS'] + player_games['AST']
            pa = pa.dropna()
            if len(pa) > 0:
                stats['pa_mean'] = round(pa.mean(), 2)
                stats['pa_std'] = round(pa.std(), 2)
        
        if all(col in player_games.columns for col in ['PTS', 'AST', 'TRB']):
            pra = player_games['PTS'] + player_games['AST'] + player_games['TRB']
            pra = pra.dropna()
            if len(pra) > 0:
                stats['pra_mean'] = round(pra.mean(), 2)
                stats['pra_std'] = round(pra.std(), 2)
        
        return stats
    
    def get_rolling_average(self, player_name: str, stat: str, window: int = 10) -> float:
        """
        Get rolling average for last N games.
        
        Args:
            player_name: Player's full name
            stat: Stat name (e.g., 'PTS', 'AST', 'TOV')
            window: Number of games
            
        Returns:
            Rolling average value
        """
        player_games = self.gamelogs[self.gamelogs['player_name'] == player_name].copy()
        
        if player_games.empty or stat not in player_games.columns:
            return 0.0
        
        recent = player_games.sort_values('Date', ascending=False).head(window)
        values = recent[stat].dropna()
        if len(values) == 0:
            return 0.0
        return round(values.mean(), 2)
    
    def compare_recent_vs_season(self, player_name: str, stat: str = 'PTS') -> Dict:
        """
        Compare recent form (last 10 games) vs full season.
        
        Args:
            player_name: Player's full name
            stat: Stat to compare
            
        Returns:
            Comparison dict
        """
        season_stats = self.get_player_stats(player_name)
        recent_stats = self.get_player_stats(player_name, last_n_games=10)
        
        if not season_stats or not recent_stats:
            return {'error': f'No data for {player_name}'}
        
        stat_key = f'{stat.lower()}_mean'
        season_avg = season_stats.get(stat_key, 0)
        recent_avg = recent_stats.get(stat_key, 0)
        difference = recent_avg - season_avg
        
        return {
            'player': player_name,
            'stat': stat,
            'season_avg': season_avg,
            'last_10_avg': recent_avg,
            'difference': round(difference, 2),
            'trend': 'HOT 🔥' if difference > 2 else 'COLD ❄️' if difference < -2 else 'STEADY'
        }

# Test the enhanced calculator
if __name__ == "__main__":
    calc = EnhancedStatsCalculator()
    
    print("Enhanced Stats Calculator Test\n" + "="*60)
    
    # Test 1: Get Curry's full stats with variance
    print("\nTest 1: Stephen Curry - Full Season Stats")
    curry_stats = calc.get_player_stats("Stephen Curry")
    print(f"  Games: {curry_stats['games_analyzed']}")
    print(f"  Points: {curry_stats['pts_mean']} ± {curry_stats['pts_std']} (range: {curry_stats['pts_min']}-{curry_stats['pts_max']})")
    print(f"  Assists: {curry_stats['ast_mean']} ± {curry_stats['ast_std']}")
    print(f"  Points + Assists: {curry_stats['pa_mean']} ± {curry_stats['pa_std']}")
    
    # Test 2: Rolling average
    print("\n" + "="*60)
    print("\nTest 2: Curry's Last 10 Games Average")
    last_10_pts = calc.get_rolling_average("Stephen Curry", "PTS", 10)
    last_10_ast = calc.get_rolling_average("Stephen Curry", "AST", 10)
    print(f"  Last 10 PPG: {last_10_pts}")
    print(f"  Last 10 APG: {last_10_ast}")
    
    # Test 3: Recent form comparison
    print("\n" + "="*60)
    print("\nTest 3: Recent Form vs Season")
    comparison = calc.compare_recent_vs_season("Stephen Curry", "PTS")
    print(f"  Season Avg: {comparison['season_avg']}")
    print(f"  Last 10 Avg: {comparison['last_10_avg']}")
    print(f"  Difference: {comparison['difference']:+.1f}")
    print(f"  Trend: {comparison['trend']}")
    
    # Test 4: Compare multiple players
    print("\n" + "="*60)
    print("\nTest 4: Multiple Players Recent Form")
    for player in ["Giannis Antetokounmpo", "Nikola Jokić", "Luka Dončić"]:
        comp = calc.compare_recent_vs_season(player, "PTS")
        print(f"  {player}: {comp['last_10_avg']} PPG (L10) vs {comp['season_avg']} (Season) - {comp['trend']}")
    
    print("\n" + "="*60)
    print("\nAll tests complete!")