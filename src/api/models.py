"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import datetime


class LegInput(BaseModel):
    """Single parlay leg input with matchup context"""
    player: str = Field(..., min_length=1, max_length=100, description="Player's full name")
    stat_type: str = Field(
        ..., 
        pattern="^(points|assists|rebounds|three_p|steals|blocks|points_assists|points_rebounds_assists)$",
        description="Statistical category to analyze"
    )
    line: float = Field(..., ge=0, le=200, description="Betting line value")
    bet_type: str = Field(..., pattern="^(over|under)$", description="Over or under the line")
    
    # NEW: Matchup context parameters
    location: Optional[str] = Field(
        None, 
        pattern="^(home|away|neutral)$",
        description="Game location: home (player's home court), away, or neutral"
    )
    opponent: Optional[str] = Field(
        None, 
        min_length=3,
        max_length=3,
        description="Opponent team 3-letter abbreviation (e.g., 'BOS', 'LAL')"
    )
    
    @validator('opponent')
    def validate_opponent_uppercase(cls, v):
        """Ensure opponent is uppercase for consistency"""
        if v:
            return v.upper()
        return v
    
    @validator('player')
    def validate_player_name(cls, v):
        """Clean up player name"""
        if v:
            # Remove extra whitespace, capitalize properly
            return ' '.join(word.capitalize() for word in v.strip().split())
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "player": "Luka Dončić",
                "stat_type": "points",
                "line": 28.5,
                "bet_type": "over",
                "location": "home",
                "opponent": "BOS"
            }
        }


class ParlayInput(BaseModel):
    """Multiple leg parlay input"""
    legs: List[LegInput] = Field(..., min_items=1, max_items=10, description="List of parlay legs (max 10)")
    
    class Config:
        schema_extra = {
            "example": {
                "legs": [
                    {
                        "player": "Stephen Curry",
                        "stat_type": "points",
                        "line": 25.5,
                        "bet_type": "over",
                        "location": "home",
                        "opponent": "LAL"
                    },
                    {
                        "player": "LeBron James",
                        "stat_type": "assists",
                        "line": 7.5,
                        "bet_type": "over",
                        "location": "away",
                        "opponent": "GSW"
                    }
                ]
            }
        }


class LegResponse(BaseModel):
    """Analysis result for single leg"""
    player: str
    stat_type: str
    line: float
    bet_type: str
    season_avg: float
    season_std: float
    recent_avg: float
    predicted_value: Optional[float] = None  # NEW: Adjusted prediction
    probability: float
    edge: float
    recommendation: str
    confidence_80: List[float]
    games_analyzed: Optional[int] = None
    adjustments_applied: Optional[dict] = None  # NEW: Shows what adjustments were made
    
    class Config:
        schema_extra = {
            "example": {
                "player": "Luka Dončić",
                "stat_type": "points",
                "line": 28.5,
                "bet_type": "over",
                "season_avg": 28.2,
                "season_std": 8.3,
                "recent_avg": 29.9,
                "predicted_value": 26.1,
                "probability": 0.584,
                "edge": 0.084,
                "recommendation": "HIT",
                "confidence_80": [17.5, 34.7],
                "games_analyzed": 65,
                "adjustments_applied": {
                    "location": 0.95,
                    "defense": {
                        "opponent": "BOS",
                        "rating": 110.6,
                        "factor": 0.978
                    }
                }
            }
        }


class ParlayResponse(BaseModel):
    """Complete parlay analysis"""
    legs: List[dict]
    num_legs: int
    combined_probability: float
    combined_percentage: str
    estimated_odds: str
    expected_value: float
    recommendation: str


class UserRegister(BaseModel):
    """User registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class UserLogin(BaseModel):
    """User login"""
    email: EmailStr
    password: str
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "user@example.com"
            }
        }


class UsageStatus(BaseModel):
    """Usage limit status"""
    allowed: bool
    remaining: int
    total_limit: int
    message: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "allowed": True,
                "remaining": 5,
                "total_limit": 7,
                "message": None
            }
        }