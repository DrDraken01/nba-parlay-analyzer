"""
Enhanced Stats Calculator - Database Version
Simplified for reliability - no complex caching
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
import os
import psycopg2
from psycopg2 import pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedStatsCalculator:
    """Calculate stats using database - simplified and reliable."""
    
    _connection_pool = None
    _pool_version = "v4"
    _current_version = None
    
    def __init__(self):
        """Initialize with database connection."""
        try:
            if (EnhancedStatsCalculator._connection_pool is None or 
                EnhancedStatsCalculator._current_version != self._pool_version):
                
                if EnhancedStatsCalculator._connection_pool:
                    logger.info("Closing old connection pool")
                    try:
                        EnhancedStatsCalculator._connection_pool.closeall()
                    except:
                        pass
                
                host = os.getenv('PGHOST')
                port = os.getenv('PGPORT', '5432')
                user = os.getenv('PGUSER')
                password = os.getenv('PGPASSWORD')
                dbname = os.getenv('PGDATABASE')
                
                logger.info(f"Creating new connection pool (version {self._pool_version})")
                
                if all([host, user, password, dbname]):
                    database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
                    
                    EnhancedStatsCalculator._connection_pool = psycopg2.pool.SimpleConnectionPool(
                        1, 10,
                        database_url
                    )
                    EnhancedStatsCalculator._current_version = self._pool_version
                    logger.info(f"Successfully connected to database at {host}")
                else:
                    missing = []
                    if not host: missing.append("PGHOST")
                    if not user: missing.append("PGUSER")
                    if not password: missing.append("PGPASSWORD")
                    if not dbname: missing.append("PGDATABASE")
                    raise ValueError(f"Missing database credentials: {', '.join(missing)}")
            
            self.conn = EnhancedStatsCalculator._connection_pool.getconn()
            self._gamelogs_cache = None
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        """Load game logs from database."""
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
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            numeric_cols = ['pts', 'ast', 'trb', 'three_p', 'stl', 'blk', 'tov', 'mp']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            df = df.dropna(subset=['date', 'pts'])
            
            logger.info(f"DEBUG: Sample players from DB: {df['player_name'].unique()[:10].tolist()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_player_stats(self, player_name: str, last_n_games: Optional[int] = None) -> Dict:
        """Get player statistics with real variance - SIMPLE AND DIRECT."""
        
        logger.info(f"=== Searching for: '{player_name}' ===")
        logger.info(f"Total games in cache: {len(self.gamelogs)}")
        
        if self.gamelogs.empty:
            logger.error("Gamelogs dataframe is EMPTY!")
            return {}
        
        # Direct case-insensitive search
        player_games = self.gamelogs[
            self.gamelogs['player_name'].str.lower() == player_name.lower()
        ].copy()
        
        logger.info(f"Found {len(player_games)} total games for '{player_name}'")
        
        if player_games.empty:
            logger.warning(f"No games found. Available players sample: {self.gamelogs['player_name'].unique()[:5].tolist()}")
            return {}
        
        # Sort by date and limit
        player_games = player_games.sort_values('date', ascending=False)
        if last_n_games:
            player_games = player_games.head(last_n_games)
        
        logger.info(f"Using {len(player_games)} games for analysis")
        
        stats = {
            'player': player_name,
            'games_analyzed': len(player_games),
            'timeframe': f'Last {last_n_games} games' if last_n_games else 'Full season'
        }
        
        # Calculate mean/std for each stat
        stat_cols = ['pts', 'ast', 'trb', 'three_p', 'stl', 'blk']
        for stat in stat_cols:
            if stat in player_games.columns:
                values = player_games[stat].dropna()
                if len(values) > 0:
                    stats[f'{stat}_mean'] = round(float(values.mean()), 2)
                    stats[f'{stat}_std'] = round(float(values.std()), 2)
                    stats[f'{stat}_min'] = int(values.min())
                    stats[f'{stat}_max'] = int(values.max())
        
        # Combo stats
        if all(col in player_games.columns for col in ['pts', 'ast']):
            pa = (player_games['pts'] + player_games['ast']).dropna()
            if len(pa) > 0:
                stats['pa_mean'] = round(float(pa.mean()), 2)
                stats['pa_std'] = round(float(pa.std()), 2)
        
        if all(col in player_games.columns for col in ['pts', 'ast', 'trb']):
            pra = (player_games['pts'] + player_games['ast'] + player_games['trb']).dropna()
            if len(pra) > 0:
                stats['pra_mean'] = round(float(pra.mean()), 2)
                stats['pra_std'] = round(float(pra.std()), 2)
        
        return stats
    
    def get_rolling_average(self, player_name: str, stat: str, window: int = 10) -> float:
        """Get rolling average for last N games."""
        stats = self.get_player_stats(player_name, last_n_games=window)
        return stats.get(f'{stat}_mean', 0.0)
    
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
    
    def close(self):
        """Return connection to pool."""
        if self.conn and EnhancedStatsCalculator._connection_pool:
            try:
                EnhancedStatsCalculator._connection_pool.putconn(self.conn)
                logger.info("Connection returned to pool")
            except:
                pass
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()