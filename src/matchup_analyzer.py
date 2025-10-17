"""
Matchup-Aware Parlay Analyzer
Considers opponent defense, historical matchups, and situational factors
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from src.enhanced_stats_calculator import EnhancedStatsCalculator
from src.probability_model import ProbabilityModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MatchupAnalyzer:
    """Advanced analyzer that considers matchup-specific factors."""
    
    # NBA Team Defensive Ratings (2024-25 season) - Lower is better
    TEAM_DEFENSIVE_RATINGS = {
        'OKC': 104.3,  # Best defense
        'HOU': 106.1,
        'ORL': 106.8,
        'LAL': 108.2,
        'BOS': 108.9,
        'MIA': 109.1,
        'GSW': 109.5,
        'CLE': 109.8,
        'MEM': 110.2,
        'NYK': 110.5,
        'DAL': 110.8,
        'MIN': 111.0,
        'DEN': 111.3,
        'MIL': 111.5,
        'PHI': 111.8,
        'SAC': 112.0,
        'LAC': 112.2,
        'PHX': 112.5,
        'NOP': 113.0,
        'ATL': 113.5,
        'IND': 114.2,
        'TOR': 114.5,
        'CHI': 114.8,
        'BKN': 115.0,
        'POR': 115.5,
        'DET': 115.8,
        'CHA': 116.0,
        'SAS': 116.5,
        'UTA': 117.0,
        'WAS': 117.5,  # Worst defense
    }
    
    # Pace factors (possessions per game)
    TEAM_PACE = {
        'IND': 103.5,  # Fastest
        'NOP': 102.8,
        'SAC': 102.3,
        'ATL': 101.5,
        'BOS': 101.2,
        'GSW': 100.8,
        'DAL': 100.5,
        'PHX': 100.2,
        'MEM': 100.0,
        'MIN': 99.8,
        'DEN': 99.5,
        'LAL': 99.3,
        'MIL': 99.0,
        'CLE': 98.8,
        'PHI': 98.5,
        'CHI': 98.3,
        'HOU': 98.0,
        'OKC': 97.8,
        'NYK': 97.5,
        'LAC': 97.3,
        'TOR': 97.0,
        'POR': 96.8,
        'BKN': 96.5,
        'MIA': 96.3,
        'ORL': 96.0,
        'DET': 95.8,
        'SAS': 95.5,
        'CHA': 95.3,
        'WAS': 95.0,
        'UTA': 94.5,  # Slowest
    }
    
    def __init__(self):
        self.stats_calc = EnhancedStatsCalculator()
        self.prob_model = ProbabilityModel()
        
        # Load game logs for matchup history
        try:
            self.gamelogs = pd.read_csv('data/gamelogs_2024.csv')
            # Clean data
            self.gamelogs = self.gamelogs[self.gamelogs['PTS'] != 'Inactive']
            self.gamelogs = self.gamelogs[self.gamelogs['PTS'] != 'Did Not Play']
            numeric_cols = ['PTS', 'AST', 'TRB', '3P', 'STL', 'BLK', 'TOV']
            for col in numeric_cols:
                if col in self.gamelogs.columns:
                    self.gamelogs[col] = pd.to_numeric(self.gamelogs[col], errors='coerce')
        except Exception as e:
            logger.warning(f"Could not load game logs for matchup analysis: {e}")
            self.gamelogs = pd.DataFrame()
    
    def analyze_leg_with_matchup(
        self, 
        player_name: str, 
        stat_type: str, 
        line: float, 
        bet_type: str = 'over',
        opponent: Optional[str] = None,
        is_home: bool = True
    ) -> Dict:
        """
        Analyze leg with matchup-specific adjustments.
        
        Args:
            player_name: Player's full name
            stat_type: Stat to analyze
            line: Betting line
            bet_type: 'over' or 'under'
            opponent: Opponent team abbreviation (e.g., 'OKC')
            is_home: Whether playing at home
            
        Returns:
            Enhanced analysis with matchup factors
        """
        # Get base stats
        base_stats = self.stats_calc.get_player_stats(player_name)
        
        if not base_stats:
            return {'error': f'Player {player_name} not found'}
        
        # Map stat type
        stat_map = {
            'points': 'pts',
            'assists': 'ast',
            'rebounds': 'trb',
            'three_pointers': '3p',
            'steals': 'stl',
            'blocks': 'blk',
            'turnovers': 'tov',
            'points_assists': 'pa',
            'points_rebounds_assists': 'pra'
        }
        
        stat_key = stat_map.get(stat_type)
        if not stat_key:
            return {'error': f'Invalid stat type: {stat_type}'}
        
        mean_key = f'{stat_key}_mean'
        std_key = f'{stat_key}_std'
        
        if mean_key not in base_stats:
            return {'error': f'No data for {player_name} - {stat_type}'}
        
        season_avg = base_stats[mean_key]
        season_std = base_stats.get(std_key, season_avg * 0.3)
        
        # Apply matchup adjustments
        adjusted_avg = season_avg
        adjustments = []
        
        if opponent:
            # 1. Defensive rating adjustment
            def_adjustment = self._get_defensive_adjustment(opponent, stat_type)
            adjusted_avg *= def_adjustment
            adjustments.append({
                'factor': 'Defense',
                'team': opponent,
                'multiplier': round(def_adjustment, 3),
                'description': self._describe_defense(opponent)
            })
            
            # 2. Pace adjustment
            pace_adjustment = self._get_pace_adjustment(opponent)
            adjusted_avg *= pace_adjustment
            adjustments.append({
                'factor': 'Pace',
                'team': opponent,
                'multiplier': round(pace_adjustment, 3),
                'description': self._describe_pace(opponent)
            })
            
            # 3. Historical matchup performance
            matchup_data = self._get_matchup_history(player_name, opponent, stat_key)
            if matchup_data['games'] > 0:
                # Blend matchup average with season average (weighted by sample size)
                weight = min(matchup_data['games'] / 10, 0.4)  # Max 40% weight
                adjusted_avg = (adjusted_avg * (1 - weight)) + (matchup_data['avg'] * weight)
                adjustments.append({
                    'factor': 'Matchup History',
                    'games': matchup_data['games'],
                    'vs_avg': round(matchup_data['avg'], 2),
                    'description': f"Last {matchup_data['games']} games vs {opponent}"
                })
        
        # 4. Home/Away adjustment
        home_adjustment = 1.05 if is_home else 0.95
        adjusted_avg *= home_adjustment
        adjustments.append({
            'factor': 'Home/Away',
            'multiplier': round(home_adjustment, 3),
            'description': 'Home' if is_home else 'Away'
        })
        
        # Calculate probability with adjusted values
        prediction = self.prob_model.predict_with_confidence(
            player_avg=adjusted_avg,
            line=line,
            variance=season_std
        )
        
        # Get recent form
        recent_stats = self.stats_calc.get_player_stats(player_name, last_n_games=10)
        recent_avg = recent_stats.get(mean_key, season_avg) if recent_stats else season_avg
        
        # Determine hit probability
        hit_probability = prediction['prob_over'] if bet_type.lower() == 'over' else prediction['prob_under']
        
        return {
            'player': player_name,
            'stat_type': stat_type,
            'line': line,
            'bet_type': bet_type.upper(),
            'opponent': opponent,
            'location': 'Home' if is_home else 'Away',
            'season_avg': season_avg,
            'adjusted_avg': round(adjusted_avg, 2),
            'adjustment_magnitude': round((adjusted_avg / season_avg - 1) * 100, 1),  # % change
            'recent_avg': recent_avg,
            'probability': round(hit_probability, 3),
            'confidence_80': prediction['confidence_80'],
            'recommendation': self._make_recommendation(hit_probability),
            'adjustments': adjustments,
            'analysis_quality': 'Enhanced' if opponent else 'Basic'
        }
    
    def _get_defensive_adjustment(self, opponent: str, stat_type: str) -> float:
        """
        Calculate adjustment based on opponent defense.
        
        Returns multiplier (e.g., 0.95 = 5% harder, 1.05 = 5% easier)
        """
        def_rating = self.TEAM_DEFENSIVE_RATINGS.get(opponent, 112.0)  # League average
        league_avg = 112.0
        
        # Better defense (lower rating) = harder to score
        # Scale: Top defense (104) = 0.92x, Worst defense (117.5) = 1.08x
        adjustment = 1 + ((league_avg - def_rating) / league_avg * 0.6)
        
        return max(0.85, min(1.15, adjustment))
    
    def _get_pace_adjustment(self, opponent: str) -> float:
        """
        Calculate adjustment based on opponent pace.
        
        Returns multiplier based on possessions per game.
        """
        pace = self.TEAM_PACE.get(opponent, 98.5)  # League average
        league_avg = 98.5
        
        # Faster pace = more opportunities
        adjustment = 1 + ((pace - league_avg) / league_avg * 0.3)
        
        return max(0.95, min(1.05, adjustment))
    
    def _get_matchup_history(self, player_name: str, opponent: str, stat_key: str) -> Dict:
        """Get player's historical performance vs specific opponent."""
        if self.gamelogs.empty or 'Opp' not in self.gamelogs.columns:
            return {'games': 0, 'avg': 0}
        
        # Filter for this player vs this opponent
        matchup_games = self.gamelogs[
            (self.gamelogs['player_name'] == player_name) & 
            (self.gamelogs['Opp'] == opponent)
        ]
        
        if matchup_games.empty:
            return {'games': 0, 'avg': 0}
        
        # Get the stat column (convert from our key to CSV column)
        csv_col = stat_key.upper()
        if csv_col not in matchup_games.columns:
            return {'games': 0, 'avg': 0}
        
        values = matchup_games[csv_col].dropna()
        
        return {
            'games': len(values),
            'avg': round(values.mean(), 2) if len(values) > 0 else 0
        }
    
    def _describe_defense(self, opponent: str) -> str:
        """Describe opponent's defensive strength."""
        def_rating = self.TEAM_DEFENSIVE_RATINGS.get(opponent, 112.0)
        
        if def_rating < 108:
            return "Elite defense (Top 5)"
        elif def_rating < 111:
            return "Above average defense"
        elif def_rating < 114:
            return "Average defense"
        elif def_rating < 116:
            return "Below average defense"
        else:
            return "Poor defense (Bottom 5)"
    
    def _describe_pace(self, opponent: str) -> str:
        """Describe opponent's pace."""
        pace = self.TEAM_PACE.get(opponent, 98.5)
        
        if pace > 101:
            return "Fast pace (more possessions)"
        elif pace > 98:
            return "Average pace"
        else:
            return "Slow pace (fewer possessions)"
    
    def _make_recommendation(self, probability: float) -> str:
        """Make betting recommendation."""
        if probability >= 0.60:
            return "STRONG HIT ✅"
        elif probability >= 0.55:
            return "LEAN HIT ↗️"
        elif probability >= 0.50:
            return "TOSS-UP ⚖️"
        elif probability >= 0.45:
            return "LEAN MISS ↘️"
        else:
            return "STRONG MISS ❌"