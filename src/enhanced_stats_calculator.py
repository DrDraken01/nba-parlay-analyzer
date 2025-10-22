"""
Enhanced Stats Calculator - Database Version
Uses Railway's PG environment variables
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
    
    _connection_pool = None
    _pool_version = "v3"
    _current_version = None

    def __init__(self):
        """Initialize with database connection - uses Railway's PG variables."""
        try:
            if EnhancedStatsCalculator._connection_pool is None:
                # Railway provides these automatically
                host = os.getenv('PGHOST')
                port = os.getenv('PGPORT', '5432')
                user = os.getenv('PGUSER')
                password = os.getenv('PGPASSWORD')
                dbname = os.getenv('PGDATABASE')
                
                if all([host, user, password, dbname]):
                    database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
                    
                    EnhancedStatsCalculator._connection_pool = psycopg2.pool.SimpleConnectionPool(
                        1, 10,
                        database_url
                    )
                    logger.info(f"Connected to database at {host}")
                else:
                    raise ValueError(f"Missing database credentials")
            
            self.conn = EnhancedStatsCalculator._connection_pool.getconn()
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
            if not self._gamelogs_cache.empty:
                logger.info(f"Loaded {len(self._gamelogs_cache)} games for {self._gamelogs_cache['player_name'].nunique()} players")
        return self._gamelogs_cache
    
    def _load_from_database(self) -> pd.DataFrame:
        """Load game logs from database with optimized query."""
        if not self.conn:
            logger.error("No database connection available")
            return pd.DataFrame()
        
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
            WHERE pts IS NOT NULL
            ORDER BY player_name, date DESC
        """
        try:
            df = pd.read_sql(query, self.conn)

            # Debug: Print first few rows
            logger.info(f"Loaded {len(df)} rows from database")
            if not df.empty:
                logger.info(f"Sample player names: {df['player_name'].unique()[:5]}")
                
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            numeric_cols = ['pts', 'ast', 'trb', 'three_p', 'stl', 'blk', 'tov', 'mp']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
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
        
        if last_n:
            player_games = player_games.head(last_n)
        
        return tuple(player_games.to_records(index=False))
    
    def get_player_stats(self, player_name: str, last_n_games: Optional[int] = None) -> Dict:
        """Get player statistics with real variance - OPTIMIZED."""
        
        # DEBUG: Log what we're fetching
        logger.info(f"Searching for player: '{player_name}'")
        logger.info(f"Total rows in gamelogs: {len(self.gamelogs)}")
        if not self.gamelogs.empty:
            unique_players = self.gamelogs['player_name'].unique()
            logger.info(f"DEBUG: Total unique players: {len(unique_players)}")
            logger.info(f"DEBUG: First 10 players: {unique_players[:10].tolist()}")
        else:
            logger.error("DEBUG:Gamelogs DataFrame is empty")

        cached_games = self._get_player_games_cached(player_name, last_n_games)
        
        if not cached_games:
            logger.warning(f"No game log data for {player_name}")
            #DEBUG: Show all unique player names
            if not self.gamelogs.empty:
                all_players = self.gamelogs['player_name'].unique()
                logger.info(f"Available players: {all_players[:10].tolist()}")
            return {}
        
        player_games = pd.DataFrame(list(cached_games))
        
        stats = {
            'player': player_name,
            'games_analyzed': len(player_games),
            'timeframe': f'Last {last_n_games} games' if last_n_games else 'Full season'
        }
        
        stat_cols = ['pts', 'ast', 'trb', 'three_p', 'stl', 'blk']
        for stat in stat_cols:
            if stat in player_games.columns:
                values = player_games[stat].dropna()
                if len(values) > 0:
                    stats[f'{stat}_mean'] = round(float(np.mean(values)), 2)
                    stats[f'{stat}_std'] = round(float(np.std(values, ddof=1)), 2)
                    stats[f'{stat}_min'] = int(np.min(values))
                    stats[f'{stat}_max'] = int(np.max(values))
        
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
        """Get rolling average for last N games."""
        return self.get_player_stats(player_name, last_n_games=window).get(f'{stat}_mean', 0.0)
    
    def compare_recent_vs_season(self, player_name: str, stat: str = 'pts') -> Dict:
        """Compare recent form vs full season."""
        season_stats = self.get_player_stats(player_name)
        recent_stats = self.get_player_stats(player_name, last_n_games=10)
        
        if not season_stats or not recent_stats:
            return {'error': f'No data for {player_name}'}
        
        stat_key = f'{stat}_mean'
        season_avg = season_stats.get(stat_key, 0)
        recent_avg = recent_stats.get(stat_key, 0)
        difference = recent_avg - season_avg
        
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
        """Return connection to pool."""
        if self.conn and EnhancedStatsCalculator._connection_pool:
            EnhancedStatsCalculator._connection_pool.putconn(self.conn)
            logger.info("Connection returned to pool")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
