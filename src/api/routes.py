"""
API routes with matchup analysis support
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from src.api.models import LegInput, ParlayInput
from src.api.auth import get_current_user, decode_token
from src.matchup_analyzer import MatchupAnalyzer
from src.usage_limiter import UsageLimiter
from src.results_tracker import ResultsTracker
import uuid

router = APIRouter()

# Initialize analyzers
analyzer = MatchupAnalyzer()
limiter = UsageLimiter()
tracker = ResultsTracker()


async def get_optional_user(authorization: Optional[str] = Header(None)) -> dict:
    """Optional authentication - returns user if authenticated, else anonymous."""
    if authorization and authorization.startswith('Bearer '):
        try:
            token = authorization.replace('Bearer ', '')
            payload = decode_token(token)
            email = payload.get('sub')
            
            if email:
                return {
                    'email': email,
                    'is_authenticated': True
                }
        except:
            pass
    
    return {
        'email': f'anonymous_{uuid.uuid4().hex[:8]}',
        'is_authenticated': False
    }


@router.post("/analyze-leg", response_model=dict)
async def analyze_leg(
    leg: LegInput,
    user: dict = Depends(get_optional_user)
):
    """
    Analyze single parlay leg with optional matchup data.
    
    If opponent is provided, includes defensive rating, pace, and head-to-head adjustments.
    """
    user_id = user['email']
    is_authenticated = user['is_authenticated']
    
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=is_authenticated)
    
    if not can_use['allowed']:
        raise HTTPException(
            status_code=429,
            detail={
                "message": can_use['message'],
                "wellness_note": can_use.get('wellness_note'),
                "reset_time": can_use.get('reset_time')
            }
        )
    
    # Perform analysis with matchup awareness
    result = analyzer.analyze_leg_with_matchup(
        player_name=leg.player,
        stat_type=leg.stat_type,
        line=leg.line,
        bet_type=leg.bet_type,
        opponent=leg.opponent,
        is_home=leg.is_home
    )
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    # Record usage
    limiter.record_usage(user_id)
    
    # Add usage info
    result['usage'] = {
        'remaining': can_use['remaining'],
        'total_limit': can_use.get('total_limit', 7 if is_authenticated else 5),
        'is_authenticated': is_authenticated
    }
    
    return result


@router.post("/analyze-parlay", response_model=dict)
async def analyze_parlay(
    parlay: ParlayInput,
    user: dict = Depends(get_optional_user)
):
    """Analyze complete multi-leg parlay with matchup data."""
    user_id = user['email']
    is_authenticated = user['is_authenticated']
    
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=is_authenticated)
    
    if not can_use['allowed']:
        raise HTTPException(status_code=429, detail=can_use['message'])
    
    analyzed_legs = []
    
    # Analyze each leg
    for leg in parlay.legs:
        result = analyzer.analyze_leg_with_matchup(
            player_name=leg.player,
            stat_type=leg.stat_type,
            line=leg.line,
            bet_type=leg.bet_type,
            opponent=leg.opponent,
            is_home=leg.is_home
        )
        
        if 'error' not in result:
            analyzed_legs.append(result)
    
    if not analyzed_legs:
        raise HTTPException(status_code=404, detail="No valid legs to analyze")
    
    # Calculate combined probability
    combined_prob = 1.0
    for leg in analyzed_legs:
        combined_prob *= leg['probability']
    
    # Record usage
    limiter.record_usage(user_id)
    
    # Calculate estimated odds
    def calculate_parlay_odds(num_legs: int) -> float:
        odds_map = {2: 2.64, 3: 5.96, 4: 12.28, 5: 24.35}
        return odds_map.get(num_legs, 2 ** num_legs)
    
    estimated_odds = calculate_parlay_odds(len(analyzed_legs))
    expected_value = (combined_prob * estimated_odds) - 1
    
    return {
        'legs': analyzed_legs,
        'num_legs': len(analyzed_legs),
        'combined_probability': round(combined_prob, 4),
        'combined_percentage': f"{combined_prob * 100:.2f}%",
        'estimated_odds': f"+{int(estimated_odds * 100)}",
        'expected_value': round(expected_value, 3),
        'recommendation': make_parlay_recommendation(combined_prob, len(analyzed_legs))
    }


def make_parlay_recommendation(combined_prob: float, num_legs: int) -> str:
    """Make recommendation for the parlay."""
    threshold = 0.15 + (num_legs * 0.02)
    
    if combined_prob >= threshold:
        return f"✅ PLAYABLE (Good value at {combined_prob*100:.1f}%)"
    elif combined_prob >= threshold * 0.7:
        return f"⚠️ MARGINAL (Borderline at {combined_prob*100:.1f}%)"
    else:
        return f"❌ AVOID (Too risky at {combined_prob*100:.1f}%)"


@router.get("/usage", response_model=dict)
async def get_usage_status(user: dict = Depends(get_optional_user)):
    """Get current usage statistics."""
    user_id = user['email']
    stats = limiter.get_usage_stats(user_id)
    stats['is_authenticated'] = user['is_authenticated']
    return stats


@router.get("/player/{player_name}")
async def get_player_info(player_name: str):
    """Get player information (not rate limited)."""
    from src.enhanced_stats_calculator import EnhancedStatsCalculator
    
    calc = EnhancedStatsCalculator()
    stats = calc.get_player_stats(player_name)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return stats


# Protected endpoints
@router.get("/results/summary")
async def get_results_summary(user: dict = Depends(get_current_user)):
    """Get betting performance summary (authenticated only)."""
    user_id = user['email']
    summary = tracker.get_performance_summary(user_id)
    return summary