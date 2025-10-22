"""
Analysis API endpoints
"""

from fastapi import APIRouter, HTTPException
from src.api.models import LegInput, ParlayInput, LegResponse, ParlayResponse, UsageStatus
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
    leg: LegInput
):
    """
    Analyze single parlay leg (auth temporarily disabled for testing)
    """
    # Temporary: Skip rate limiting for testing
    can_use = {'allowed': True, 'remaining': 999, 'total_limit': 999}
    
    # Perform analysis
    result = analyzer.analyze_leg(
        leg.player,
        leg.stat_type,
        leg.line,
        leg.bet_type
    )
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    # Add remaining count to response
    result['usage'] = {
        'remaining': can_use['remaining'],
        'total_limit': can_use.get('total_limit', 999)
    }
    
    return result


@router.post("/analyze-parlay", response_model=ParlayResponse)
async def analyze_parlay(
    parlay: ParlayInput
):
    """
    Analyze complete multi-leg parlay (auth temporarily disabled)
    """
    # Temporary: Skip rate limiting
    can_use = {'allowed': True, 'remaining': 999, 'total_limit': 999}
    
    # Convert to format analyzer expects
    legs_data = [leg.dict() for leg in parlay.legs]
    
    # Perform analysis
    result = analyzer.analyze_parlay(legs_data)
    
    return result


@router.get("/usage", response_model=dict)
async def get_usage_status():
    """Get current usage statistics (auth disabled for testing)"""
    return {
        'count_today': 0,
        'total_lifetime': 0,
        'remaining': 999
    }


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