"""
API Models - Complete Version
Includes both authentication models AND matchup analysis models
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List


# ==================== AUTHENTICATION MODELS ====================

class UserRegister(BaseModel):
    """User registration input."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login input."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    """User information."""
    email: str
    id: Optional[int] = None


# ==================== PARLAY ANALYSIS MODELS ====================

class LegInput(BaseModel):
    """Single parlay leg input with matchup data."""
    player: str = Field(..., description="Player's full name")
    stat_type: str = Field(..., description="Stat to analyze")
    line: float = Field(..., description="Betting line")
    bet_type: str = Field(default="over", description="'over' or 'under'")
    opponent: Optional[str] = Field(None, description="Opponent team abbreviation (e.g., 'OKC')")
    is_home: bool = Field(True, description="Whether playing at home")


class LegResponse(BaseModel):
    """Analysis result for a single leg."""
    player: str
    stat_type: str
    line: float
    bet_type: str
    season_avg: float
    adjusted_avg: Optional[float] = None
    recent_avg: float
    probability: float
    recommendation: str
    confidence_80: List[float]
    opponent: Optional[str] = None
    adjustments: Optional[List[dict]] = None


class ParlayInput(BaseModel):
    """Multi-leg parlay input."""
    legs: List[LegInput]


class ParlayResponse(BaseModel):
    """Complete parlay analysis."""
    legs: List[dict]
    num_legs: int
    combined_probability: float
    combined_percentage: str
    estimated_odds: str
    expected_value: float
    recommendation: str


class UsageStatus(BaseModel):
    """User's usage statistics."""
    user_id: str
    analyses_today: int
    daily_limit: int
    remaining: int
    reset_time: str