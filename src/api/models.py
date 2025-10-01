"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime


class LegInput(BaseModel):
    """Single parlay leg input"""
    player: str = Field(..., min_length=1, max_length=100)
    stat_type: str = Field(..., pattern="^(points|assists|rebounds|points_assists|points_rebounds_assists)$")
    line: float = Field(..., ge=0, le=200)
    bet_type: str = Field(..., pattern="^(over|under)$")


class ParlayInput(BaseModel):
    """Multiple leg parlay input"""
    legs: List[LegInput] = Field(..., min_items=1, max_items=10)


class LegResponse(BaseModel):
    """Analysis result for single leg"""
    player: str
    stat_type: str
    line: float
    bet_type: str
    season_avg: float
    season_std: float
    recent_avg: float
    probability: float
    edge: float
    recommendation: str
    confidence_80: List[float]


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
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UsageStatus(BaseModel):
    """Usage limit status"""
    allowed: bool
    remaining: int
    total_limit: int
    message: Optional[str] = None