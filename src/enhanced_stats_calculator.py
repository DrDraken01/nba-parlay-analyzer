"""
Enhanced Stats Calculator - Database Version
Uses Railway PostgreSQL instead of CSV files
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
import os
import psycopg2
from psycopg2 import pool
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedStatsCalculator:
    """Calculate stats using database instead of CSV."""
    
    # Class-level connection pool (shared across instances)
    _connection_pool = None
    
    def __init__(self):
        """Initialize with database connection."""
        try:
            # Use connection pool for better performance
            if EnhancedStatsCalculator._connection_pool is None:
                EnhancedStatsCalculator._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 10,  # min and max connections
                    dbname=os.getenv('DB_NAME'),
                    user=os.getenv('DB_USER'),
                    password=os.getenv('DB_PASSWORD'),
                    host=os.getenv('DB_HOST'),
                    port=os.getenv('DB_PORT', '5432')
                )
            
            self.conn = EnhancedStatsCalculator._connection_pool.getconn()
            
            # Load game logs from database - LAZY LOADING
            # Don't load all data at init - only when needed
            self._gamelogs_cache = None
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self.conn = None
            self._gamelogs_cache = pd.DataFrame()
    
    @property
    def gamelogs(self) -> pd.DataFrame:
        """Lazy load gamelogs only when accessed."""
        if self._gamelogs_cache is None:
            self._gamelogs_cache = self._load_from_database()
            logger.info(f"Loaded {len(self._gamelogs_cache)} games for {self._gamelogs_cache['player_name'].nunique()} players")
        return self._gamelogs_cache
    
    def _load_from_database(self) -> pd.DataFrame:
        """Load game logs from database with optimized query."""
        if not self.conn:
            return pd.DataFrame()
        
        # Optimized query: only select what we need, let DB do the sorting
        query = """
            SELECT 
                player_name, 
                date, 
                opponent, 
                pts, 
                ast, 
                trb, 
                three_p, 
                stl, 
                blk, 
                tov, 
                mp
            FROM game_logs
            WHERE pts IS NOT NULL  -- Filter at DB level
            ORDER BY player_name, date DESC  -- Pre-sort for efficient player lookups
        """
        try:
            df = pd.read_sql(query, self.conn)
            
            # Convert date to datetime (more efficient with errors='coerce')
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Ensure numeric columns are numeric (vectorized operation)
            numeric_cols = ['pts', 'ast', 'trb', 'three_p', 'stl', 'blk', 'tov', 'mp']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            
            # Drop rows with NaN in critical columns (already filtered pts at DB level)
            df = df.dropna(subset=['date', 'pts'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return pd.DataFrame()
    
    @lru_cache(maxsize=128)
    def _get_player_games_cached(self, player_name: str, last_n: Optional[int] = None) -> tuple:
        """Cache player game data to avoid repeated DataFrame operations."""
        player_games = self.gamelogs[self.gamelogs['player_name'] == player_name].copy()
        
        if player_games.empty:
            return tuple()
        
        # Already sorted by date DESC from database query
        if last_n:
            player_games = player_games.head(last_n)
        
        # Return as tuple of tuples for caching (DataFrames aren't hashable)
        return tuple(player_games.to_records(index=False))
    
    def get_player_stats(self, player_name: str, last_n_games: Optional[int] = None) -> Dict:
        """Get player statistics with real variance - OPTIMIZED."""
        
        # Try to get from cache first
        cached_games = self._get_player_games_cached(player_name, last_n_games)
        
        if not cached_games:
            logger.warning(f"No game log data for {player_name}")
            return {}
        
        # Convert back to DataFrame for calculations
        player_games = pd.DataFrame(list(cached_games))
        
        stats = {
            'player': player_name,
            'games_analyzed': len(player_games),
            'timeframe': f'Last {last_n_games} games' if last_n_games else 'Full season'
        }
        
        # Vectorized calculations for all stats at once (much faster)
        stat_cols = ['pts', 'ast', 'trb', 'three_p', 'stl', 'blk']
        for stat in stat_cols:
            if stat in player_games.columns:
                values = player_games[stat].dropna()
                if len(values) > 0:
                    # Use numpy for faster calculations
                    stats[f'{stat}_mean'] = round(float(np.mean(values)), 2)
                    stats[f'{stat}_std'] = round(float(np.std(values, ddof=1)), 2)
                    stats[f'{stat}_min'] = int(np.min(values))
                    stats[f'{stat}_max'] = int(np.max(values))
        
        # Calculate combo stats efficiently
        if all(col in player_games.columns for col in ['pts', 'ast']):
            pa = (player_games['pts'] + player_games['ast']).dropna()
            if len(pa) > 0:
                stats['pa_mean'] = round(float(np.mean(pa)), 2)
                stats['pa_std'] = round(float(np.std(pa, ddof=1)), 2)
        
        if all(col in player_games.columns for col in ['pts', 'ast', 'trb']):
            pra = (player_games['pts'] + player_games['ast'] + player_games['trb']).dropna()
            if len(pra) > 0:
                stats['pra_mean'] = round(float(np.mean(pra)), 2)
                stats['pra_std'] = round(float(np.std(pra, ddof=1)), 2)
        
        return stats
    
    def get_rolling_average(self, player_name: str, stat: str, window: int = 10) -> float:
        """Get rolling average for last N games - uses cached data."""
        # Reuse the cached method
        return self.get_player_stats(player_name, last_n_games=window).get(f'{stat}_mean', 0.0)
    
    def compare_recent_vs_season(self, player_name: str, stat: str = 'pts') -> Dict:
        """Compare recent form vs full season - OPTIMIZED."""
        # Get both stats in parallel (could be optimized further with threading)
        season_stats = self.get_player_stats(player_name)
        recent_stats = self.get_player_stats(player_name, last_n_games=10)
        
        if not season_stats or not recent_stats:
            return {'error': f'No data for {player_name}'}
        
        stat_key = f'{stat}_mean'
        season_avg = season_stats.get(stat_key, 0)
        recent_avg = recent_stats.get(stat_key, 0)
        difference = recent_avg - season_avg
        
        # More granular trend detection
        if difference > 3:
            trend = 'VERY HOT 🔥🔥'
        elif difference > 1.5:
            trend = 'HOT 🔥'
        elif difference < -3:
            trend = 'VERY COLD ❄️❄️'
        elif difference < -1.5:
            trend = 'COLD ❄️'
        else:
            trend = 'STEADY ➡️'
        
        return {
            'player': player_name,
            'stat': stat,
            'season_avg': season_avg,
            'last_10_avg': recent_avg,
            'difference': round(difference, 2),
            'trend': trend,
            'sample_size': {
                'season': season_stats.get('games_analyzed', 0),
                'recent': recent_stats.get('games_analyzed', 0)
            }
        }
    
    def clear_cache(self):
        """Clear the LRU cache if needed."""
        self._get_player_games_cached.cache_clear()
    
    def close(self):
        """Return connection to pool instead of closing."""
        if self.conn and EnhancedStatsCalculator._connection_pool:
            EnhancedStatsCalculator._connection_pool.putconn(self.conn)
            logger.info("Connection returned to pool")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
