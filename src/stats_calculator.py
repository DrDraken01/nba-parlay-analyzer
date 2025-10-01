"""
Player Statistics Calculator
Calculates rolling averages, matchup stats, and performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import psycopg2
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)
load_dotenv()


class StatsCalculator:
    """Calculate various statistical metrics for players."""
    
    def __init__(self):
        """Initialize with database connection."""
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', '5432')
        )
    
    def get_player_season_avg(self, player_name: str, season: int = 2025) -> Dict:
        """
        Get player's season averages.
        
        Args:
            player_name: Player's full name
            season: NBA season year
            
        Returns:
            Dictionary with season averages
        """
        cursor = self.conn.cursor()
        
        # For now, we'll use the CSV data since we don't have game logs yet
        # In production, this would query player_game_stats table
        
        try:
            df = pd.read_csv('data/players_2024_25.csv')
            player_data = df[df['Player'] == player_name]
            
            if player_data.empty:
                logger.warning(f"No data found for {player_name}")
                return {}
            
            row = player_data.iloc[0]
            
            return {
                'player': player_name,
                'team': row['Team'],
                'games': int(row['G']) if pd.notna(row['G']) else 0,
                'minutes': float(row['MP']) if pd.notna(row['MP']) else 0,
                'points': float(row['PTS']) if pd.notna(row['PTS']) else 0,
                'assists': float(row['AST']) if pd.notna(row['AST']) else 0,
                'rebounds': float(row['TRB']) if pd.notna(row['TRB']) else 0,
                'steals': float(row['STL']) if pd.notna(row['STL']) else 0,
                'blocks': float(row['BLK']) if pd.notna(row['BLK']) else 0,
                'three_pointers': float(row['3P']) if pd.notna(row['3P']) else 0,
                'turnovers': float(row['TOV']) if pd.notna(row['TOV']) else 0,
                'fg_pct': float(row['FG%']) if pd.notna(row['FG%']) else 0,
                'points_assists': float(row['PTS']) + float(row['AST']) if pd.notna(row['PTS']) and pd.notna(row['AST']) else 0,
                'points_rebounds_assists': float(row['PTS']) + float(row['TRB']) + float(row['AST']) if all(pd.notna(row[x]) for x in ['PTS', 'TRB', 'AST']) else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting season avg for {player_name}: {e}")
            return {}
        finally:
            cursor.close()
    
    def calculate_rolling_average(self, games_data: pd.DataFrame, 
                                  stat: str, window: int = 10) -> float:
        """
        Calculate rolling average for a stat.
        
        Args:
            games_data: DataFrame with game-by-game stats
            stat: Stat column name
            window: Number of games to average
            
        Returns:
            Rolling average value
        """
        if games_data.empty or stat not in games_data.columns:
            return 0.0
        
        recent_games = games_data.head(window)
        return recent_games[stat].mean()
    
    def get_matchup_history(self, player_name: str, opponent_abbr: str, 
                           last_n_games: int = 10) -> Dict:
        """
        Get player's historical performance vs specific opponent.
        
        Args:
            player_name: Player's full name
            opponent_abbr: Opponent team abbreviation
            last_n_games: Number of recent games vs opponent
            
        Returns:
            Dictionary with matchup averages
        """
        # This would query game logs from database
        # For MVP, we'll implement a simplified version
        
        return {
            'player': player_name,
            'opponent': opponent_abbr,
            'games_played': 0,
            'avg_points': 0.0,
            'avg_assists': 0.0,
            'avg_rebounds': 0.0,
            'note': 'Historical matchup data not yet available - need game logs'
        }
    
    def predict_stat_line(self, player_name: str, opponent: str, 
                         home_or_away: str = 'H') -> Dict:
        """
        Predict player's stat line for upcoming game.
        
        This is the core prediction function that will evolve into
        our full probability model.
        
        Args:
            player_name: Player's full name
            opponent: Opponent team abbreviation
            home_or_away: 'H' for home, 'A' for away
            
        Returns:
            Predicted stats with confidence intervals
        """
        # Get season averages as baseline
        season_avg = self.get_player_season_avg(player_name)
        
        if not season_avg:
            return {'error': 'Player not found'}
        
        # For MVP, we'll use season averages as predictions
        # Phase 3.5 will add adjustments for matchup, pace, etc.
        
        predictions = {
            'player': player_name,
            'opponent': opponent,
            'location': home_or_away,
            'predicted_points': season_avg['points'],
            'predicted_assists': season_avg['assists'],
            'predicted_rebounds': season_avg['rebounds'],
            'predicted_points_assists': season_avg['points_assists'],
            'predicted_pra': season_avg['points_rebounds_assists'],
            'confidence': 'medium',
            'model_version': 'v0.1_baseline',
            'notes': 'Using season averages as baseline. Matchup adjustments coming in next iteration.'
        }
        
        return predictions
    
    def calculate_over_under_probability(self, player_name: str, 
                                        stat_type: str, line: float,
                                        opponent: str = None) -> Dict:
        """
        Calculate probability of hitting over/under.
        
        This is the KEY function for parlay analysis.
        
        Args:
            player_name: Player's full name
            stat_type: 'points', 'assists', 'rebounds', 'points_assists', etc.
            line: Betting line (e.g., 25.5)
            opponent: Opponent team (optional, improves accuracy)
            
        Returns:
            Probability breakdown
        """
        season_avg = self.get_player_season_avg(player_name)
        
        if not season_avg:
            return {'error': 'Player not found'}
        
        # Get the relevant stat
        stat_value = season_avg.get(stat_type, 0)
        
        if stat_value == 0:
            return {'error': f'Invalid stat type: {stat_type}'}
        
        # Simple probability calculation (will improve with variance data)
        difference = stat_value - line
        
        # Naive probability based on distance from line
        # This is a placeholder - real model will use historical variance
        if difference > 2:
            prob_over = 0.65
        elif difference > 0:
            prob_over = 0.55
        elif difference > -2:
            prob_over = 0.45
        else:
            prob_over = 0.35
        
        prob_under = 1.0 - prob_over
        
        return {
            'player': player_name,
            'stat_type': stat_type,
            'line': line,
            'season_avg': stat_value,
            'prob_over': round(prob_over, 3),
            'prob_under': round(prob_under, 3),
            'fair_line': stat_value,
            'edge_over': round(prob_over - 0.5, 3),
            'confidence_interval_80': [stat_value - 3, stat_value + 3],
            'model_version': 'v0.1_simple',
            'recommendation': 'over' if prob_over > 0.55 else 'under' if prob_under > 0.55 else 'pass'
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Test the calculator
if __name__ == "__main__":
    calc = StatsCalculator()
    
    try:
        print("NBA Stats Calculator Test\n" + "="*60)
        
        # Test 1: Season averages
        print("\nTest 1: Stephen Curry Season Averages")
        curry_avg = calc.get_player_season_avg("Stephen Curry")
        if curry_avg:
            print(f"  Points: {curry_avg['points']}")
            print(f"  Assists: {curry_avg['assists']}")
            print(f"  Points + Assists: {curry_avg['points_assists']}")
        
        # Test 2: Prediction
        print("\n" + "="*60)
        print("\nTest 2: Predict Curry vs Lakers")
        prediction = calc.predict_stat_line("Stephen Curry", "LAL", "H")
        print(f"  Predicted Points: {prediction['predicted_points']}")
        print(f"  Predicted Assists: {prediction['predicted_assists']}")
        
        # Test 3: Over/Under Probability
        print("\n" + "="*60)
        print("\nTest 3: Curry Over 25.5 Points")
        prob = calc.calculate_over_under_probability("Stephen Curry", "points", 25.5)
        print(f"  Season Avg: {prob['season_avg']}")
        print(f"  Prob Over: {prob['prob_over']} ({prob['prob_over']*100:.1f}%)")
        print(f"  Prob Under: {prob['prob_under']} ({prob['prob_under']*100:.1f}%)")
        print(f"  Recommendation: {prob['recommendation'].upper()}")
        
        print("\n" + "="*60)
        print("\nAll tests complete!")
        
    finally:
        calc.close()