"""
Analysis API endpoints with matchup-based adjustments
AUTH TEMPORARILY DISABLED FOR TESTING
"""

from fastapi import APIRouter, HTTPException
from src.api.models import LegInput, ParlayInput, LegResponse, ParlayResponse, UsageStatus
from src.parlay_analyzer import ParlayAnalyzer
from src.usage_limiter import UsageLimiter
from src.results_tracker import ResultsTracker
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize analyzers
analyzer = ParlayAnalyzer()
limiter = UsageLimiter()
tracker = ResultsTracker()


@router.post("/analyze-leg", response_model=dict)
async def analyze_leg(leg: LegInput):
    """
    Analyze single parlay leg with matchup adjustments.
    
    NOTE: Authentication temporarily disabled for testing matchup adjustments.
    
    This endpoint accepts:
    - Player name
    - Stat type (points, assists, etc.)
    - Betting line
    - Bet direction (over/under)
    - Location (home/away/neutral) - Optional
    - Opponent team - Optional
    
    Returns probability analysis with matchup-based adjustments applied.
    """
    user_id = "test_user"  # Hardcoded for testing
    
    logger.info(f"Analysis request: {leg.player} {leg.stat_type} {leg.bet_type} {leg.line} @ {leg.location or 'neutral'} vs {leg.opponent or 'none'}")
    
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=True)
    
    if not can_use['allowed']:
        logger.warning(f"Rate limit hit: {can_use['reason']}")
        raise HTTPException(
            status_code=429,
            detail={
                "message": can_use['message'],
                "wellness_note": can_use.get('wellness_note'),
                "reset_time": can_use.get('reset_time')
            }
        )
    
    # Perform analysis with matchup context
    try:
        result = analyzer.analyze_leg(
            player_name=leg.player,
            stat_type=leg.stat_type,
            line=leg.line,
            bet_type=leg.bet_type,
            location=leg.location or 'neutral',
            opponent=leg.opponent
        )
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
    
    if 'error' in result:
        logger.warning(f"Analysis returned error: {result['error']}")
        raise HTTPException(status_code=404, detail=result['error'])
    
    # Record usage
    limiter.record_usage(user_id)
    logger.info(f"Analysis complete: {result['probability']:.1%} probability")
    
    # Add remaining count to response
    result['usage'] = {
        'remaining': can_use['remaining'],
        'total_limit': can_use.get('total_limit', 7)
    }
    
    return result


@router.post("/analyze-parlay", response_model=ParlayResponse)
async def analyze_parlay(parlay: ParlayInput):
    """
    Analyze complete multi-leg parlay with matchup adjustments.
    
    AUTH DISABLED FOR TESTING.
    """
    user_id = "test_user"
    
    logger.info(f"Parlay analysis request: {len(parlay.legs)} legs")
    
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=True)
    
    if not can_use['allowed']:
        logger.warning(f"Rate limit hit")
        raise HTTPException(status_code=429, detail=can_use['message'])
    
    # Convert to format analyzer expects
    legs_data = []
    for leg in parlay.legs:
        leg_dict = {
            'player': leg.player,
            'stat_type': leg.stat_type,
            'line': leg.line,
            'bet_type': leg.bet_type,
            'location': leg.location or 'neutral',
            'opponent': leg.opponent
        }
        legs_data.append(leg_dict)
    
    # Perform analysis
    try:
        result = analyzer.analyze_parlay(legs_data)
    except Exception as e:
        logger.error(f"Parlay analysis error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Parlay analysis failed: {str(e)}"
        )
    
    if 'error' in result:
        logger.warning(f"Parlay analysis returned error: {result['error']}")
        raise HTTPException(status_code=400, detail=result['error'])
    
    # Record usage
    limiter.record_usage(user_id)
    logger.info(f"Parlay analysis complete: {result['combined_percentage']} combined")
    
    # Log for results tracking
    try:
        parlay_id = tracker.log_parlay(user_id, result)
        result['parlay_id'] = parlay_id
        logger.debug(f"Logged parlay with ID: {parlay_id}")
    except Exception as e:
        logger.error(f"Failed to log parlay for tracking: {str(e)}")
    
    return result


@router.get("/usage", response_model=dict)
async def get_usage_status():
    """Get current usage statistics (no auth required for testing)."""
    user_id = "test_user"
    
    try:
        stats = limiter.get_usage_stats(user_id)
        logger.debug(f"Usage stats: {stats['count_today']} today")
        return stats
    except Exception as e:
        logger.error(f"Error getting usage stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage stats")


@router.get("/player/{player_name}")
async def get_player_info(player_name: str):
    """
    Get player information and statistics.
    
    This endpoint is NOT rate limited as it's reference data only.
    """
    logger.debug(f"Player info request: {player_name}")
    
    from src.enhanced_stats_calculator import EnhancedStatsCalculator
    
    calc = EnhancedStatsCalculator()
    
    try:
        stats = calc.get_player_stats(player_name)
        
        if not stats:
            logger.warning(f"Player not found: {player_name}")
            raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")
        
        logger.debug(f"Player info retrieved: {player_name}")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player info for {player_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve player information")
    finally:
        calc.close()


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        from src.enhanced_stats_calculator import EnhancedStatsCalculator
        calc = EnhancedStatsCalculator()
        
        has_data = not calc.gamelogs.empty
        calc.close()
        
        return {
            "status": "healthy",
            "auth": "disabled_for_testing",
            "components": {
                "database": "connected" if has_data else "no_data",
                "analyzer": "operational",
                "limiter": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "error": str(e)
        }


@router.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "NBA Parlay Analyzer API",
        "version": "2.0.0",
        "auth_status": "DISABLED FOR TESTING",
        "features": [
            "Matchup-based probability adjustments",
            "Home/away court factors",
            "Opponent defensive rating integration",
            "Real variance from game logs",
            "Rate limiting (7 per day for testing)"
        ],
        "documentation": "/docs"
    }