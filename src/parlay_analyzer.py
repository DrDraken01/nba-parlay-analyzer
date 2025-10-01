"""
Parlay Analyzer - Integrated with Enhanced Stats Calculator
Analyzes multi-leg parlays and calculates combined probabilities
"""

from src.enhanced_stats_calculator import EnhancedStatsCalculator
from src.probability_model import ProbabilityModel
from typing import List, Dict
import pandas as pd


class ParlayAnalyzer:
    """Analyze complete parlays with multiple legs."""
    
    def __init__(self):
        self.stats_calc = EnhancedStatsCalculator()
        self.prob_model = ProbabilityModel()
    
    def analyze_leg(self, player_name: str, stat_type: str, 
                   line: float, bet_type: str = 'over') -> Dict:
        """
        Analyze a single parlay leg.
        
        Args:
            player_name: Player's full name
            stat_type: 'points', 'assists', 'points_assists', etc.
            line: Betting line
            bet_type: 'over' or 'under'
            
        Returns:
            Analysis with probability and recommendation
        """
        # Get player's season stats with REAL variance from game logs
        season_stats = self.stats_calc.get_player_stats(player_name)
        
        if not season_stats:
            return {'error': f'Player {player_name} not found'}
        
        # Map stat_type to our data keys
        stat_map = {
            'points': 'pts',
            'assists': 'ast',
            'rebounds': 'trb',
            'points_assists': 'pa',
            'points_rebounds_assists': 'pra'
        }
        
        stat_key = stat_map.get(stat_type, stat_type)
        mean_key = f'{stat_key}_mean'
        std_key = f'{stat_key}_std'
        
        if mean_key not in season_stats:
            return {'error': f'Invalid stat type: {stat_type}'}
        
        player_stat_avg = season_stats[mean_key]
        player_stat_std = season_stats.get(std_key, player_stat_avg * 0.3)
        
        # Calculate probability with REAL variance
        prediction = self.prob_model.predict_with_confidence(
            player_avg=player_stat_avg,
            line=line,
            variance=player_stat_std
        )
        
        # Get recent form for context
        recent_stats = self.stats_calc.get_player_stats(player_name, last_n_games=10)
        recent_avg = recent_stats.get(mean_key, player_stat_avg) if recent_stats else player_stat_avg
        
        # Determine the probability for the bet type
        if bet_type.lower() == 'over':
            hit_probability = prediction['prob_over']
            edge = prediction['edge_over']
        else:
            hit_probability = prediction['prob_under']
            edge = prediction['edge_under']
        
        return {
            'player': player_name,
            'stat_type': stat_type,
            'line': line,
            'bet_type': bet_type.upper(),
            'season_avg': player_stat_avg,
            'season_std': player_stat_std,
            'recent_avg': recent_avg,
            'predicted_value': prediction['adjusted_mean'],
            'probability': round(hit_probability, 3),
            'edge': round(edge, 3),
            'confidence_80': prediction['confidence_80'],
            'recommendation': 'HIT' if hit_probability > 0.55 else 'MISS' if hit_probability < 0.45 else 'TOSS-UP'
        }
    
    def analyze_parlay(self, legs: List[Dict]) -> Dict:
        """
        Analyze complete parlay with multiple legs.
        
        Args:
            legs: List of leg dicts with keys: player, stat_type, line, bet_type
            
        Returns:
            Complete parlay analysis
        """
        analyzed_legs = []
        
        # Analyze each leg
        for leg in legs:
            result = self.analyze_leg(
                leg['player'],
                leg['stat_type'],
                leg['line'],
                leg.get('bet_type', 'over')
            )
            analyzed_legs.append(result)
        
        # Calculate combined probability (assuming independence)
        combined_prob = 1.0
        for leg in analyzed_legs:
            if 'probability' in leg:
                combined_prob *= leg['probability']
        
        # Calculate expected value (simplified)
        estimated_odds = self._calculate_parlay_odds(len(legs))
        expected_value = (combined_prob * estimated_odds) - 1
        
        return {
            'legs': analyzed_legs,
            'num_legs': len(legs),
            'combined_probability': round(combined_prob, 4),
            'combined_percentage': f"{combined_prob * 100:.2f}%",
            'estimated_odds': f"+{int(estimated_odds * 100)}",
            'expected_value': round(expected_value, 3),
            'recommendation': self._make_parlay_recommendation(combined_prob, len(legs))
        }
    
    def _calculate_parlay_odds(self, num_legs: int) -> float:
        """
        Estimate parlay payout odds.
        
        Args:
            num_legs: Number of legs in parlay
            
        Returns:
            Payout multiplier (e.g., 3.0 = +200)
        """
        odds_map = {
            2: 2.64,
            3: 5.96,
            4: 12.28,
            5: 24.35,
        }
        return odds_map.get(num_legs, 2 ** num_legs)
    
    def _make_parlay_recommendation(self, combined_prob: float, num_legs: int) -> str:
        """Make recommendation for the parlay."""
        threshold = 0.15 + (num_legs * 0.02)
        
        if combined_prob >= threshold:
            return f"✅ PLAYABLE (Good value at {combined_prob*100:.1f}%)"
        elif combined_prob >= threshold * 0.7:
            return f"⚠️ MARGINAL (Borderline at {combined_prob*100:.1f}%)"
        else:
            return f"❌ AVOID (Too risky at {combined_prob*100:.1f}%)"
    
    def compare_parlays(self, parlay_a: List[Dict], parlay_b: List[Dict]) -> Dict:
        """
        Compare two parlays side-by-side.
        
        Args:
            parlay_a: First parlay legs
            parlay_b: Second parlay legs
            
        Returns:
            Comparison analysis
        """
        analysis_a = self.analyze_parlay(parlay_a)
        analysis_b = self.analyze_parlay(parlay_b)
        
        return {
            'parlay_a': analysis_a,
            'parlay_b': analysis_b,
            'better_option': 'A' if analysis_a['combined_probability'] > analysis_b['combined_probability'] else 'B',
            'probability_difference': abs(analysis_a['combined_probability'] - analysis_b['combined_probability'])
        }
    
    def close(self):
        """Close connections (placeholder for future cleanup)."""
        pass