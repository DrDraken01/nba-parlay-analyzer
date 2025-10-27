"""
Parlay Analyzer - Integrated with Enhanced Stats Calculator
Analyzes multi-leg parlays and calculates combined probabilities
with matchup-based adjustments
"""

from src.enhanced_stats_calculator import EnhancedStatsCalculator
from src.probability_model import ProbabilityModel
from src.team_stats import (
    get_location_factor, 
    get_team_defense, 
    calculate_defense_factor,
    get_defense_impact_description
)
from typing import List, Dict, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ParlayAnalyzer:
    """Analyze complete parlays with multiple legs and matchup adjustments."""
    
    def __init__(self):
        self.stats_calc = EnhancedStatsCalculator()
        self.prob_model = ProbabilityModel()
    
    def analyze_leg(self, player_name: str, stat_type: str, 
                   line: float, bet_type: str = 'over',
                   location: str = 'neutral', 
                   opponent: Optional[str] = None) -> Dict:
        """
        Analyze a single parlay leg with full matchup context.
        
        Args:
            player_name: Player's full name
            stat_type: 'points', 'assists', 'rebounds', 'three_p', 'steals', 
                      'blocks', 'points_assists', 'points_rebounds_assists'
            line: Betting line
            bet_type: 'over' or 'under'
            location: 'home', 'away', or 'neutral'
            opponent: 3-letter team abbreviation (e.g., 'BOS', 'LAL')
            
        Returns:
            Analysis with probability and recommendation, including adjustments
        """
        logger.info(f"Analyzing: {player_name} {stat_type} {bet_type} {line} @ {location} vs {opponent}")
        
        # Get player's season stats with REAL variance from game logs
        season_stats = self.stats_calc.get_player_stats(player_name)
        
        if not season_stats:
            logger.warning(f"Player not found: {player_name}")
            return {'error': f'Player {player_name} not found'}
        
        # Map stat_type to our data keys
        stat_map = {
            'points': 'pts',
            'assists': 'ast',
            'rebounds': 'trb',
            'three_p': 'three_p',
            'steals': 'stl',
            'blocks': 'blk',
            'points_assists': 'pa',
            'points_rebounds_assists': 'pra'
        }
        
        stat_key = stat_map.get(stat_type, stat_type)
        mean_key = f'{stat_key}_mean'
        std_key = f'{stat_key}_std'
        
        if mean_key not in season_stats:
            logger.error(f"Invalid stat type: {stat_type}")
            return {'error': f'Invalid stat type: {stat_type}'}
        
        player_stat_avg = season_stats[mean_key]
        player_stat_std = season_stats.get(std_key, player_stat_avg * 0.3)
        
        logger.debug(f"Player stats - Avg: {player_stat_avg}, Std: {player_stat_std}")
        
        # Build adjustments dictionary
        adjustments = {}
        
        # Add location adjustment
        location_factor = get_location_factor(location)
        if location_factor != 1.0:  # Only include if not neutral
            adjustments['location'] = location_factor
            logger.debug(f"Location factor ({location}): {location_factor}")
        
        # Add opponent defense adjustment
        if opponent:
            opp_def_rating = get_team_defense(opponent)
            defense_factor = calculate_defense_factor(opp_def_rating)
            
            adjustments['defense'] = {
                'opponent': opponent,
                'rating': opp_def_rating,
                'factor': defense_factor,
                'description': get_defense_impact_description(opponent)
            }
            logger.debug(f"Defense adjustment vs {opponent}: factor={defense_factor}, rating={opp_def_rating}")
        
        # Calculate probability with adjustments
        prediction = self.prob_model.predict_with_confidence(
            player_avg=player_stat_avg,
            line=line,
            variance=player_stat_std,
            adjustments=adjustments if adjustments else None
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
        
        # Build response
        result = {
            'player': player_name,
            'stat_type': stat_type,
            'line': line,
            'bet_type': bet_type.upper(),
            'season_avg': round(player_stat_avg, 2),
            'season_std': round(player_stat_std, 2),
            'recent_avg': round(recent_avg, 2),
            'predicted_value': prediction['adjusted_mean'],
            'probability': round(hit_probability, 4),
            'edge': round(edge, 4),
            'confidence_80': prediction['confidence_80'],
            'recommendation': 'HIT' if hit_probability > 0.55 else 'MISS' if hit_probability < 0.45 else 'TOSS-UP',
            'games_analyzed': season_stats.get('games_analyzed', 0)
        }
        
        # Add adjustment details if any were applied
        if adjustments:
            result['adjustments_applied'] = adjustments
            result['adjustment_summary'] = prediction.get('adjustments_summary', {})
        
        logger.info(f"Result: {hit_probability:.1%} probability, recommendation: {result['recommendation']}")
        
        return result
    
    def analyze_parlay(self, legs: List[Dict]) -> Dict:
        """
        Analyze complete parlay with multiple legs.
        
        Args:
            legs: List of leg dicts with keys: player, stat_type, line, bet_type, 
                  location (optional), opponent (optional)
            
        Returns:
            Complete parlay analysis
        """
        logger.info(f"Analyzing {len(legs)}-leg parlay")
        
        analyzed_legs = []
        
        # Analyze each leg
        for i, leg in enumerate(legs, 1):
            logger.info(f"Processing leg {i}/{len(legs)}")
            
            result = self.analyze_leg(
                leg['player'],
                leg['stat_type'],
                leg['line'],
                leg.get('bet_type', 'over'),
                leg.get('location', 'neutral'),
                leg.get('opponent')
            )
            
            if 'error' in result:
                logger.error(f"Leg {i} failed: {result['error']}")
                # Include error but continue
                result['leg_number'] = i
            
            analyzed_legs.append(result)
        
        # Calculate combined probability (assuming independence)
        # Note: This is a simplification - in reality, some correlations may exist
        combined_prob = 1.0
        valid_legs = 0
        
        for leg in analyzed_legs:
            if 'probability' in leg:
                combined_prob *= leg['probability']
                valid_legs += 1
        
        if valid_legs == 0:
            return {
                'error': 'No valid legs to analyze',
                'legs': analyzed_legs
            }
        
        # Calculate expected value
        estimated_odds = self._calculate_parlay_odds(valid_legs)
        expected_value = (combined_prob * estimated_odds) - 1
        
        # Identify weakest leg (lowest probability)
        weakest_leg = None
        if analyzed_legs:
            valid_analyzed = [l for l in analyzed_legs if 'probability' in l]
            if valid_analyzed:
                weakest_leg = min(valid_analyzed, key=lambda x: x['probability'])
        
        result = {
            'legs': analyzed_legs,
            'num_legs': len(legs),
            'valid_legs': valid_legs,
            'combined_probability': round(combined_prob, 4),
            'combined_percentage': f"{combined_prob * 100:.2f}%",
            'estimated_odds': f"+{int((estimated_odds - 1) * 100)}",
            'expected_value': round(expected_value, 3),
            'recommendation': self._make_parlay_recommendation(combined_prob, valid_legs),
            'weakest_leg': weakest_leg['player'] if weakest_leg else None
        }
        
        logger.info(f"Parlay result: {result['combined_percentage']} combined probability")
        
        return result
    
    def _calculate_parlay_odds(self, num_legs: int) -> float:
        """
        Estimate parlay payout odds based on number of legs.
        
        These are typical sportsbook payouts (includes house edge).
        
        Args:
            num_legs: Number of legs in parlay
            
        Returns:
            Payout multiplier (e.g., 3.0 = +200 = 2:1)
        """
        # Typical sportsbook parlay payouts
        odds_map = {
            1: 1.91,   # -110 (single bet)
            2: 2.64,   # +164
            3: 5.96,   # +496
            4: 12.28,  # +1128
            5: 24.35,  # +2435
            6: 47.41,  # +4741
            7: 91.42,  # +9142
            8: 175.45, # +17445
            9: 335.85, # +33485
            10: 642.08 # +64108
        }
        
        return odds_map.get(num_legs, 2 ** num_legs)
    
    def _make_parlay_recommendation(self, combined_prob: float, num_legs: int) -> str:
        """
        Make recommendation for the parlay.
        
        Logic: As legs increase, required probability increases
        (due to compounding unlikely events)
        
        Args:
            combined_prob: Combined probability of all legs hitting
            num_legs: Number of legs
            
        Returns:
            Recommendation string
        """
        # Base threshold + adjustment for number of legs
        # 2-leg: 15%, 3-leg: 17%, 4-leg: 19%, etc.
        threshold = 0.15 + (num_legs - 2) * 0.02
        
        if combined_prob >= threshold * 1.5:
            return f"✅ STRONG PLAY (Excellent value at {combined_prob*100:.1f}%)"
        elif combined_prob >= threshold:
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
        
        better = 'A' if analysis_a['combined_probability'] > analysis_b['combined_probability'] else 'B'
        
        return {
            'parlay_a': analysis_a,
            'parlay_b': analysis_b,
            'better_option': better,
            'probability_difference': abs(
                analysis_a['combined_probability'] - analysis_b['combined_probability']
            ),
            'ev_difference': abs(
                analysis_a['expected_value'] - analysis_b['expected_value']
            )
        }
    
    def close(self):
        """Close connections."""
        if hasattr(self.stats_calc, 'close'):
            self.stats_calc.close()


# Test the analyzer
if __name__ == "__main__":
    analyzer = ParlayAnalyzer()
    
    print("Parlay Analyzer Test with Matchup Adjustments\n" + "="*70)
    
    # Test 1: Single leg - Neutral
    print("\n📊 Test 1: Luka 28.5 PTS, Neutral Court, No Opponent")
    result1 = analyzer.analyze_leg(
        "Luka Dončić",
        "points",
        28.5,
        "over",
        location="neutral",
        opponent=None
    )
    if 'error' not in result1:
        print(f"  Season Avg: {result1['season_avg']}")
        print(f"  Predicted: {result1['predicted_value']}")
        print(f"  Probability: {result1['probability']} ({result1['probability']*100:.1f}%)")
        print(f"  Recommendation: {result1['recommendation']}")
    else:
        print(f"  Error: {result1['error']}")
    
    # Test 2: Same player, Home vs weak defense
    print("\n" + "="*70)
    print("📊 Test 2: Luka 28.5 PTS, HOME vs Charlotte")
    result2 = analyzer.analyze_leg(
        "Luka Dončić",
        "points",
        28.5,
        "over",
        location="home",
        opponent="CHA"
    )
    if 'error' not in result2:
        print(f"  Season Avg: {result2['season_avg']}")
        print(f"  Predicted: {result2['predicted_value']} (adjusted up!)")
        print(f"  Probability: {result2['probability']} ({result2['probability']*100:.1f}%)")
        print(f"  Adjustments: {result2.get('adjustment_summary', {})}")
        print(f"  Recommendation: {result2['recommendation']}")
    else:
        print(f"  Error: {result2['error']}")
    
    # Test 3: Same player, Away vs elite defense
    print("\n" + "="*70)
    print("📊 Test 3: Luka 28.5 PTS, AWAY vs Boston")
    result3 = analyzer.analyze_leg(
        "Luka Dončić",
        "points",
        28.5,
        "over",
        location="away",
        opponent="BOS"
    )
    if 'error' not in result3:
        print(f"  Season Avg: {result3['season_avg']}")
        print(f"  Predicted: {result3['predicted_value']} (adjusted down!)")
        print(f"  Probability: {result3['probability']} ({result3['probability']*100:.1f}%)")
        print(f"  Adjustments: {result3.get('adjustment_summary', {})}")
        print(f"  Recommendation: {result3['recommendation']}")
    else:
        print(f"  Error: {result3['error']}")
    
    # Compare results
    print("\n" + "="*70)
    print("📊 COMPARISON: Matchup Impact on Same Bet")
    if all('error' not in r for r in [result1, result2, result3]):
        print(f"  Neutral: {result1['probability']*100:.1f}%")
        print(f"  Home vs CHA: {result2['probability']*100:.1f}%")
        print(f"  Away vs BOS: {result3['probability']*100:.1f}%")
        print(f"  Spread: {(result2['probability'] - result3['probability'])*100:.1f} points!")
        print("\n  ✅ Matchups matter! Same bet, different probabilities.")
    
    # Test 4: Multi-leg parlay
    print("\n" + "="*70)
    print("📊 Test 4: 3-Leg Parlay with Matchups")
    parlay = [
        {
            'player': 'Stephen Curry',
            'stat_type': 'points',
            'line': 25.5,
            'bet_type': 'over',
            'location': 'home',
            'opponent': 'LAL'
        },
        {
            'player': 'LeBron James',
            'stat_type': 'points',
            'line': 24.5,
            'bet_type': 'over',
            'location': 'away',
            'opponent': 'GSW'
        },
        {
            'player': 'Giannis Antetokounmpo',
            'stat_type': 'points',
            'line': 30.5,
            'bet_type': 'over',
            'location': 'neutral'
        }
    ]
    
    parlay_result = analyzer.analyze_parlay(parlay)
    if 'error' not in parlay_result:
        print(f"  Legs: {parlay_result['num_legs']}")
        print(f"  Combined Probability: {parlay_result['combined_percentage']}")
        print(f"  Expected Odds: {parlay_result['estimated_odds']}")
        print(f"  Recommendation: {parlay_result['recommendation']}")
        print(f"  Weakest Leg: {parlay_result.get('weakest_leg')}")
    
    analyzer.close()
    
    print("\n" + "="*70)
    print("✅ All tests complete!")