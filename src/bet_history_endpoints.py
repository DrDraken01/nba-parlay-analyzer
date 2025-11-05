"""
Bet History API Endpoints for FastAPI
Add these to your main FastAPI app
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .bet_history_db_postgres import BetHistoryDB

# Initialize database
bet_db = BetHistoryDB()

# Create router (you can add this to your main app)
router = APIRouter(prefix="/api", tags=["bet-history"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateBetRequest(BaseModel):
    playerName: str
    statType: str
    line: float
    probability: float
    recommendation: str
    stake: Optional[float] = 100.0
    odds: Optional[float] = 1.9

class UpdateBetResultRequest(BaseModel):
    result: str  # 'won' or 'lost'

class BetResponse(BaseModel):
    id: int
    playerName: str
    statType: str
    line: float
    probability: float
    recommendation: str
    result: str
    stake: float
    odds: float
    timestamp: str

class BetHistoryResponse(BaseModel):
    bets: List[BetResponse]
    stats: dict


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/bet-history")
async def get_bet_history():
    """
    GET /api/bet-history
    Returns all bets with statistics
    """
    try:
        bets = bet_db.get_all_bets()
        stats = bet_db.get_stats()
        
        return {
            "bets": bets,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bet history: {str(e)}")


@router.post("/bet-history")
async def create_bet(bet: CreateBetRequest):
    """
    POST /api/bet-history
    Creates a new bet record
    
    Request body:
    {
        "playerName": "Stephen Curry",
        "statType": "3PM",
        "line": 4.5,
        "probability": 67.3,
        "recommendation": "STRONG BET",
        "stake": 100.0,
        "odds": 1.9
    }
    """
    try:
        bet_id = bet_db.create_bet(
            player_name=bet.playerName,
            stat_type=bet.statType,
            line=bet.line,
            probability=bet.probability,
            recommendation=bet.recommendation,
            stake=bet.stake,
            odds=bet.odds
        )
        
        return {
            "success": True,
            "bet_id": bet_id,
            "message": "Bet created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create bet: {str(e)}")


@router.patch("/bet-history/{bet_id}")
async def update_bet_result(bet_id: int, update: UpdateBetResultRequest):
    """
    PATCH /api/bet-history/{bet_id}
    Updates bet result to 'won' or 'lost'
    
    Request body:
    {
        "result": "won"
    }
    """
    try:
        # Validate result
        if update.result not in ['won', 'lost']:
            raise HTTPException(status_code=400, detail="Result must be 'won' or 'lost'")
        
        # Update bet
        success = bet_db.update_bet_result(bet_id, update.result)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Bet with ID {bet_id} not found")
        
        return {
            "success": True,
            "message": f"Bet {bet_id} marked as {update.result}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bet: {str(e)}")


@router.delete("/bet-history/{bet_id}")
async def delete_bet(bet_id: int):
    """
    DELETE /api/bet-history/{bet_id}
    Deletes a bet (optional - for admin purposes)
    """
    try:
        success = bet_db.delete_bet(bet_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Bet with ID {bet_id} not found")
        
        return {
            "success": True,
            "message": f"Bet {bet_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bet: {str(e)}")


# ============================================================================
# HOW TO INTEGRATE INTO YOUR MAIN APP
# ============================================================================

"""
In your main.py or app.py, add these lines:

from bet_history_endpoints import router as bet_history_router

app = FastAPI()

# Add the bet history routes
app.include_router(bet_history_router)

# Your existing routes
@app.post("/api/analyze-leg")
async def analyze_leg(...):
    ...
"""