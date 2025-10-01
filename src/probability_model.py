"""
Probability Model for Over/Under Predictions
Uses statistical methods to calculate more accurate probabilities
"""

import numpy as np
from scipy import stats
import pandas as pd
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ProbabilityModel:
    """
    Statistical model for predicting Over/Under probabilities.
    
    Uses normal distribution with variance from historical performance.
    """
    
    def __init__(self):
        """Initialize the model."""
        pass
    
    def calculate_variance(self, games_data: pd.DataFrame, stat: str) -> float:
        """
        Calculate variance for a stat from game logs.
        
        For MVP without game logs, we'll estimate variance.
        
        Args:
            games_data: DataFrame with game-by-game data
            stat: Stat column name
            
        Returns:
            Standard deviation
        """
        if games_data.empty or stat not in games_data.columns:
            # Default variance estimates by position
            # These are rough NBA averages
            variance_estimates = {
                'points': 8.0,
                'assists': 2.5,
                'rebounds': 3.0,
                'three_pointers': 1.5,
                'steals': 0.8,
                'blocks': 0.7
            }
            return variance_estimates.get(stat, 5.0)
        
        return games_data[stat].std()
    
    def calculate_probability_normal(self, mean: float, std: float, 
                                    line: float, over: bool = True) -> float:
        """
        Calculate probability using normal distribution.
        
        Args:
            mean: Player's average for the stat
            std: Standard deviation
            line: Betting line
            over: True for over, False for under
            
        Returns:
            Probability (0 to 1)
        """
        if std == 0:
            std = 1.0  # Avoid division by zero
        
        # Calculate Z-score
        z = (line - mean) / std
        
        # Get probability from normal distribution
        if over:
            # P(X > line) = 1 - CDF(line)
            prob = 1 - stats.norm.cdf(z)
        else:
            # P(X < line) = CDF(line)
            prob = stats.norm.cdf(z)
        
        return prob
    
    def adjust_for_matchup(self, base_mean: float, opponent_defensive_rating: float,
                          league_avg_rating: float = 110.0) -> float:
        """
        Adjust player's expected performance based on opponent defense.
        
        Args:
            base_mean: Player's season average
            opponent_defensive_rating: Opponent's defensive rating
            league_avg_rating: League average defensive rating
            
        Returns:
            Adjusted mean
        """
        # If opponent is 5 points better than average on defense,
        # reduce expected output by ~5%
        rating_diff = opponent_defensive_rating - league_avg_rating
        adjustment_factor = 1 - (rating_diff / 200)  # 200 is scaling factor
        
        return base_mean * adjustment_factor
    
    def adjust_for_pace(self, base_mean: float, team_pace: float,
                       opponent_pace: float, league_avg_pace: float = 100.0) -> float:
        """
        Adjust for game pace (faster = more possessions = more stats).
        
        Args:
            base_mean: Player's season average
            team_pace: Player's team pace
            opponent_pace: Opponent's pace
            league_avg_pace: League average pace
            
        Returns:
            Adjusted mean
        """
        expected_game_pace = (team_pace + opponent_pace) / 2
        pace_adjustment = expected_game_pace / league_avg_pace
        
        return base_mean * pace_adjustment
    
    def calculate_confidence_interval(self, mean: float, std: float,
                                     confidence: float = 0.80) -> Tuple[float, float]:
        """
        Calculate confidence interval for prediction.
        
        Args:
            mean: Expected value
            std: Standard deviation
            confidence: Confidence level (0.80 = 80%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        z_score = stats.norm.ppf((1 + confidence) / 2)
        margin = z_score * std
        
        return (mean - margin, mean + margin)
    
    def predict_with_confidence(self, player_avg: float, line: float,
                               variance: float = None,
                               adjustments: Dict = None) -> Dict:
        """
        Full prediction with all adjustments and confidence intervals.
        
        Args:
            player_avg: Player's season average
            line: Betting line
            variance: Standard deviation (estimated if None)
            adjustments: Dict with 'pace', 'defense', etc.
            
        Returns:
            Complete prediction breakdown
        """
        # Apply adjustments
        adjusted_mean = player_avg
        
        if adjustments:
            if 'pace' in adjustments:
                adjusted_mean = self.adjust_for_pace(
                    adjusted_mean,
                    adjustments['pace']['team'],
                    adjustments['pace']['opponent']
                )
            
            if 'defense' in adjustments:
                adjusted_mean = self.adjust_for_matchup(
                    adjusted_mean,
                    adjustments['defense']['opponent_rating']
                )
        
        # Use provided variance or estimate
        std = variance if variance else player_avg * 0.3  # 30% coefficient of variation
        
        # Calculate probabilities
        prob_over = self.calculate_probability_normal(adjusted_mean, std, line, over=True)
        prob_under = 1 - prob_over
        
        # Confidence intervals
        ci_80 = self.calculate_confidence_interval(adjusted_mean, std, 0.80)
        ci_95 = self.calculate_confidence_interval(adjusted_mean, std, 0.95)
        
        # Fair line (50th percentile)
        fair_line = adjusted_mean
        
        # Edge calculation
        edge_over = prob_over - 0.5
        edge_under = prob_under - 0.5
        
        return {
            'line': line,
            'season_avg': player_avg,
            'adjusted_mean': round(adjusted_mean, 2),
            'standard_deviation': round(std, 2),
            'prob_over': round(prob_over, 3),
            'prob_under': round(prob_under, 3),
            'fair_line': round(fair_line, 1),
            'edge_over': round(edge_over, 3),
            'edge_under': round(edge_under, 3),
            'confidence_80': [round(ci_80[0], 1), round(ci_80[1], 1)],
            'confidence_95': [round(ci_95[0], 1), round(ci_95[1], 1)],
            'recommendation': self._make_recommendation(edge_over, edge_under)
        }
    
    def _make_recommendation(self, edge_over: float, edge_under: float) -> str:
        """
        Make betting recommendation based on edge.
        
        Args:
            edge_over: Edge for over bet
            edge_under: Edge for under bet
            
        Returns:
            Recommendation string
        """
        threshold = 0.05  # Need 5% edge to recommend
        
        if edge_over >= threshold:
            return f"OVER (edge: {edge_over:+.1%})"
        elif edge_under >= threshold:
            return f"UNDER (edge: {edge_under:+.1%})"
        else:
            return "PASS (no edge)"


# Test the model
if __name__ == "__main__":
    model = ProbabilityModel()
    
    print("Probability Model Test\n" + "="*60)
    
    # Test 1: Basic probability
    print("\nTest 1: Curry 24.5 PPG vs 25.5 line")
    result = model.predict_with_confidence(
        player_avg=24.5,
        line=25.5
    )
    print(f"  Adjusted Mean: {result['adjusted_mean']}")
    print(f"  Prob Over: {result['prob_over']} ({result['prob_over']*100:.1f}%)")
    print(f"  Prob Under: {result['prob_under']} ({result['prob_under']*100:.1f}%)")
    print(f"  80% CI: {result['confidence_80']}")
    print(f"  Recommendation: {result['recommendation']}")
    
    # Test 2: With pace adjustment
    print("\n" + "="*60)
    print("\nTest 2: With pace adjustment (fast-paced game)")
    result2 = model.predict_with_confidence(
        player_avg=24.5,
        line=25.5,
        adjustments={
            'pace': {
                'team': 102,  # Warriors pace
                'opponent': 105  # Fast opponent
            }
        }
    )
    print(f"  Base Average: 24.5")
    print(f"  Adjusted Mean: {result2['adjusted_mean']} (pace boost)")
    print(f"  Prob Over: {result2['prob_over']} ({result2['prob_over']*100:.1f}%)")
    print(f"  Recommendation: {result2['recommendation']}")
    
    # Test 3: Giannis (higher average)
    print("\n" + "="*60)
    print("\nTest 3: Giannis 30.4 PPG vs 28.5 line")
    result3 = model.predict_with_confidence(
        player_avg=30.4,
        line=28.5
    )
    print(f"  Prob Over: {result3['prob_over']} ({result3['prob_over']*100:.1f}%)")
    print(f"  Fair Line: {result3['fair_line']}")
    print(f"  Recommendation: {result3['recommendation']}")
    
    print("\n" + "="*60)
    print("\nAll tests complete!")