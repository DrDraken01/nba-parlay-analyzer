"""
Analysis API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from src.api.models import LegInput, ParlayInput, LegResponse, ParlayResponse, UsageStatus
from src.api.auth import get_current_user
from src.parlay_analyzer import ParlayAnalyzer
from src.usage_limiter import UsageLimiter
from src.results_tracker import ResultsTracker

router = APIRouter()

# Initialize analyzers
analyzer = ParlayAnalyzer()
limiter = UsageLimiter()
tracker = ResultsTracker()


@router.post("/analyze-leg", response_model=dict)
async def analyze_leg(
    leg: LegInput,
    user: dict = Depends(get_current_user)
):
    """
    Analyze single parlay leg
    """
    user_id = user['email'] # Use email as identifier for limiter
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=True)
    
    if not can_use['allowed']:
        raise HTTPException(
            status_code=429,
            detail={
                "message": can_use['message'],
                "wellness_note": can_use.get('wellness_note'),
                "reset_time": can_use.get('reset_time')
            }
        )
    
    # Perform analysis
    result = analyzer.analyze_leg(
        leg.player,
        leg.stat_type,
        leg.line,
        leg.bet_type
    )
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    # Record usage
    limiter.record_usage(user_id)
    
    # Add remaining count to response
    result['usage'] = {
        'remaining': can_use['remaining'],
        'total_limit': can_use.get('total_limit', 7)
    }
    
    return result


@router.post("/analyze-parlay", response_model=ParlayResponse)
async def analyze_parlay(
    parlay: ParlayInput,
    user_id: str = Depends(get_current_user)
):
    """
    Analyze complete multi-leg parlay
    """
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=True)
    
    if not can_use['allowed']:
        raise HTTPException(status_code=429, detail=can_use['message'])
    
    # Convert to format analyzer expects
    legs_data = [leg.dict() for leg in parlay.legs]
    
    # Perform analysis
    result = analyzer.analyze_parlay(legs_data)
    
    # Record usage
    limiter.record_usage(user_id)
    
    # Log for results tracking
    parlay_id = tracker.log_parlay(user_id, result)
    result['parlay_id'] = parlay_id
    
    return result


@router.get("/usage", response_model=dict)
async def get_usage_status(user_id: str = Depends(get_current_user)):
    """Get current usage statistics"""
    stats = limiter.get_usage_stats(user_id)
    return stats


@router.get("/results/summary")
async def get_results_summary(user_id: str = Depends(get_current_user)):
    """Get betting performance summary"""
    summary = tracker.get_performance_summary(user_id)
    return summary


@router.put("/results/{parlay_id}")
async def update_result(
    parlay_id: str,
    won: bool,
    wager_amount: float = 0,
    payout: float = 0,
    user_id: str = Depends(get_current_user)
):
    """Update parlay with actual result"""
    tracker.update_result(user_id, parlay_id, won, wager_amount, payout)
    return {"message": "Result updated", "parlay_id": parlay_id}


@router.get("/player/{player_name}")
async def get_player_info(player_name: str):
    """
    Get player information (not rate limited - reference data)
    """
    from src.enhanced_stats_calculator import EnhancedStatsCalculator
    
    calc = EnhancedStatsCalculator()
    stats = calc.get_player_stats(player_name)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return stats