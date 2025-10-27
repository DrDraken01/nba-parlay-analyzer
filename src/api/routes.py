"""
Analysis API endpoints with matchup-based adjustments
"""

from fastapi import APIRouter, Depends, HTTPException
from src.api.models import LegInput, ParlayInput, LegResponse, ParlayResponse, UsageStatus
from src.api.auth import get_current_user
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
async def analyze_leg(
    leg: LegInput,
    user: dict = Depends(get_current_user)
):
    """
    Analyze single parlay leg with matchup adjustments.
    
    This endpoint accepts:
    - Player name
    - Stat type (points, assists, etc.)
    - Betting line
    - Bet direction (over/under)
    - Location (home/away/neutral) - Optional
    - Opponent team - Optional
    
    Returns probability analysis with matchup-based adjustments applied.
    """
    user_id = user['email']  # Use email as identifier for limiter
    
    logger.info(f"Analysis request from {user_id}: {leg.player} {leg.stat_type} {leg.bet_type} {leg.line}")
    
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=True)
    
    if not can_use['allowed']:
        logger.warning(f"Rate limit hit for {user_id}: {can_use['reason']}")
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
            location=leg.location or 'neutral',  # Default to neutral if not provided
            opponent=leg.opponent  # None if not provided
        )
    except Exception as e:
        logger.error(f"Analysis error for {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
    
    if 'error' in result:
        logger.warning(f"Analysis returned error: {result['error']}")
        raise HTTPException(status_code=404, detail=result['error'])
    
    # Record usage
    limiter.record_usage(user_id)
    logger.info(f"Analysis complete for {user_id}: {result['probability']:.1%} probability")
    
    # Add remaining count to response
    result['usage'] = {
        'remaining': can_use['remaining'],
        'total_limit': can_use.get('total_limit', 7)
    }
    
    return result


@router.post("/analyze-parlay", response_model=ParlayResponse)
async def analyze_parlay(
    parlay: ParlayInput,
    user: dict = Depends(get_current_user)
):
    """
    Analyze complete multi-leg parlay with matchup adjustments.
    
    Accepts multiple legs, each with optional location and opponent.
    Returns combined probability and expected value analysis.
    """
    user_id = user['email']
    
    logger.info(f"Parlay analysis request from {user_id}: {len(parlay.legs)} legs")
    
    # Check rate limit
    can_use = limiter.check_can_analyze(user_id, is_authenticated=True)
    
    if not can_use['allowed']:
        logger.warning(f"Rate limit hit for {user_id}")
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
        logger.error(f"Parlay analysis error for {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Parlay analysis failed: {str(e)}"
        )
    
    if 'error' in result:
        logger.warning(f"Parlay analysis returned error: {result['error']}")
        raise HTTPException(status_code=400, detail=result['error'])
    
    # Record usage
    limiter.record_usage(user_id)
    logger.info(f"Parlay analysis complete for {user_id}: {result['combined_percentage']} combined")
    
    # Log for results tracking
    try:
        parlay_id = tracker.log_parlay(user_id, result)
        result['parlay_id'] = parlay_id
        logger.debug(f"Logged parlay with ID: {parlay_id}")
    except Exception as e:
        logger.error(f"Failed to log parlay for tracking: {str(e)}")
        # Don't fail the request if tracking fails
    
    return result


@router.get("/usage", response_model=dict)
async def get_usage_status(user: dict = Depends(get_current_user)):
    """
    Get current usage statistics for authenticated user.
    
    Returns:
    - Analyses used today
    - Total lifetime analyses
    - Next reset time
    """
    user_id = user['email']
    
    try:
        stats = limiter.get_usage_stats(user_id)
        logger.debug(f"Usage stats for {user_id}: {stats['count_today']} today")
        return stats
    except Exception as e:
        logger.error(f"Error getting usage stats for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage stats")


@router.get("/results/summary")
async def get_results_summary(user: dict = Depends(get_current_user)):
    """
    Get betting performance summary for authenticated user.
    
    Returns win/loss record, ROI, and reality check messages.
    """
    user_id = user['email']
    
    try:
        summary = tracker.get_performance_summary(user_id)
        logger.debug(f"Performance summary for {user_id}: {summary.get('wins', 0)}W-{summary.get('losses', 0)}L")
        return summary
    except Exception as e:
        logger.error(f"Error getting results summary for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve results summary")


@router.put("/results/{parlay_id}")
async def update_result(
    parlay_id: str,
    won: bool,
    wager_amount: float = 0,
    payout: float = 0,
    user: dict = Depends(get_current_user)
):
    """
    Update parlay with actual result.
    
    Args:
    - parlay_id: ID of the parlay to update
    - won: Whether the parlay won
    - wager_amount: Amount wagered (optional)
    - payout: Amount won if successful (optional)
    """
    user_id = user['email']
    
    logger.info(f"Result update from {user_id}: parlay {parlay_id} - {'WON' if won else 'LOST'}")
    
    try:
        tracker.update_result(user_id, parlay_id, won, wager_amount, payout)
        return {
            "message": "Result updated successfully",
            "parlay_id": parlay_id,
            "outcome": "won" if won else "lost"
        }
    except Exception as e:
        logger.error(f"Error updating result for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update result")


@router.get("/player/{player_name}")
async def get_player_info(player_name: str):
    """
    Get player information and statistics.
    
    This endpoint is NOT rate limited as it's reference data only.
    Useful for autocomplete and player lookups.
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
    """
    Health check endpoint for monitoring.
    
    Returns service status and component health.
    """
    try:
        # Quick test of database connectivity
        from src.enhanced_stats_calculator import EnhancedStatsCalculator
        calc = EnhancedStatsCalculator()
        
        # Try to load gamelogs (tests database connection)
        has_data = not calc.gamelogs.empty
        calc.close()
        
        return {
            "status": "healthy",
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
    """
    Root endpoint - API information.
    """
    return {
        "name": "NBA Parlay Analyzer API",
        "version": "2.0.0",
        "features": [
            "Matchup-based probability adjustments",
            "Home/away court factors",
            "Opponent defensive rating integration",
            "Real variance from game logs",
            "Rate limiting with responsible gaming features"
        ],
        "documentation": "/docs"
    }