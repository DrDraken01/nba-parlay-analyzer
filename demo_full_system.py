"""
Complete demo of the NBA Parlay Analyzer system
Shows how all components work together
"""

from src.enhanced_stats_calculator import EnhancedStatsCalculator
from src.probability_model import ProbabilityModel
from src.parlay_analyzer import ParlayAnalyzer

print("="*70)
print("NBA PARLAY ANALYZER - COMPLETE SYSTEM DEMO")
print("="*70)

# Initialize components
stats_calc = EnhancedStatsCalculator()
prob_model = ProbabilityModel()
parlay_analyzer = ParlayAnalyzer()

# Scenario: You're analyzing a 4-leg parlay from a betting slip
print("\n📋 SCENARIO: Analyzing a 4-leg parlay")
print("-"*70)

parlay = [
    {'player': 'Stephen Curry', 'stat_type': 'points', 'line': 24.5, 'bet_type': 'over'},
    {'player': 'Giannis Antetokounmpo', 'stat_type': 'points', 'line': 29.5, 'bet_type': 'over'},
    {'player': 'Nikola Jokić', 'stat_type': 'assists', 'line': 9.5, 'bet_type': 'over'},
    {'player': 'Luka Dončić', 'stat_type': 'points_assists', 'line': 42.5, 'bet_type': 'over'}
]

print("\nYour Parlay:")
for i, leg in enumerate(parlay, 1):
    print(f"  {i}. {leg['player']} - {leg['stat_type']} {leg['bet_type']} {leg['line']}")

print("\n" + "="*70)
print("DETAILED ANALYSIS")
print("="*70)

# Analyze each leg with detailed breakdown
for i, leg in enumerate(parlay, 1):
    print(f"\n🏀 LEG {i}: {leg['player']}")
    print("-"*70)
    
    # Get player's full season stats with variance
    player_stats = stats_calc.get_player_stats(leg['player'])
    
    if player_stats:
        stat_key = leg['stat_type'].lower().replace('_', '')
        mean_key = f"{stat_key}_mean"
        std_key = f"{stat_key}_std"
        
        if mean_key in player_stats:
            season_avg = player_stats[mean_key]
            std_dev = player_stats.get(std_key, season_avg * 0.3)
            
            print(f"Season Stats:")
            print(f"  Average: {season_avg}")
            print(f"  Std Dev: {std_dev}")
            print(f"  Games: {player_stats['games_analyzed']}")
            
            # Get recent form
            recent_stats = stats_calc.get_player_stats(leg['player'], last_n_games=10)
            if recent_stats and mean_key in recent_stats:
                recent_avg = recent_stats[mean_key]
                diff = recent_avg - season_avg
                trend = "🔥 HOT" if diff > 2 else "❄️ COLD" if diff < -2 else "➡️ STEADY"
                print(f"\nRecent Form (L10):")
                print(f"  Average: {recent_avg}")
                print(f"  vs Season: {diff:+.1f}")
                print(f"  Trend: {trend}")
            
            # Calculate probability using real variance
            prediction = prob_model.predict_with_confidence(
                player_avg=season_avg,
                line=leg['line'],
                variance=std_dev
            )
            
            prob = prediction['prob_over'] if leg['bet_type'] == 'over' else prediction['prob_under']
            
            print(f"\nProbability Analysis:")
            print(f"  Line: {leg['line']}")
            print(f"  Fair Line: {prediction['fair_line']}")
            print(f"  Prob {leg['bet_type'].upper()}: {prob:.1%}")
            edge_key = f"edge_{leg['bet_type']}"
            print(f"  Edge: {prediction[edge_key]:+.1%}")
            print(f"  80% CI: {prediction['confidence_80']}")
            print(f"  Recommendation: {prediction['recommendation']}")

# Overall parlay analysis
print("\n" + "="*70)
print("PARLAY SUMMARY")
print("="*70)

result = parlay_analyzer.analyze_parlay(parlay)

print(f"\nCombined Probability: {result['combined_percentage']}")
print(f"Estimated Payout: {result['estimated_odds']}")
print(f"Expected Value: {result['expected_value']:+.3f}")
print(f"\n{result['recommendation']}")

print("\nIndividual Leg Probabilities:")
for i, leg_result in enumerate(result['legs'], 1):
    if 'probability' in leg_result:
        print(f"  Leg {i}: {leg_result['probability']:.1%} - {leg_result['recommendation']}")

# Alternative parlay suggestion
print("\n" + "="*70)
print("ALTERNATIVE PARLAY (Better Value)")
print("="*70)

alternative = [
    {'player': 'Stephen Curry', 'stat_type': 'points', 'line': 22.5, 'bet_type': 'over'},
    {'player': 'Nikola Jokić', 'stat_type': 'points', 'line': 24.5, 'bet_type': 'over'},
    {'player': 'Luka Dončić', 'stat_type': 'points', 'line': 32.5, 'bet_type': 'over'}
]

print("\nAdjusted 3-leg parlay with better lines:")
for i, leg in enumerate(alternative, 1):
    print(f"  {i}. {leg['player']} - {leg['stat_type']} {leg['bet_type']} {leg['line']}")

alt_result = parlay_analyzer.analyze_parlay(alternative)
print(f"\nCombined Probability: {alt_result['combined_percentage']}")
print(f"Estimated Payout: {alt_result['estimated_odds']}")
print(f"{alt_result['recommendation']}")

# Comparison
print("\n" + "="*70)
print("COMPARISON")
print("="*70)

comparison = parlay_analyzer.compare_parlays(parlay, alternative)
print(f"\nOriginal Parlay: {result['combined_percentage']} win probability")
print(f"Alternative Parlay: {alt_result['combined_percentage']} win probability")
print(f"\nBetter Option: Parlay {comparison['better_option']}")
print(f"Probability Difference: {comparison['probability_difference']:.2%}")

print("\n" + "="*70)
print("KEY INSIGHTS")
print("="*70)

print("""
1. Use REAL variance data from game logs for accurate probabilities
2. Check recent form (last 10 games) for hot/cold streaks
3. Lower the number of legs = higher win probability
4. Look for edges of 5%+ to justify the bet
5. Confidence intervals show the uncertainty range
""")

# Close connections
parlay_analyzer.close()

print("\n" + "="*70)
print("Demo Complete! You now have a production-ready analysis engine.")
print("="*70)