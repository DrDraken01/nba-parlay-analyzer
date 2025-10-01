"""
Authentication system - JWT tokens and user management
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

from src.api.models import UserRegister, UserLogin, Token

load_dotenv()

router = APIRouter()
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to get current user from JWT token
    Returns user_id (email for now, since we're not using database yet)
    """
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return user_id


# In-memory user storage (temporary - will move to database)
fake_users_db = {}


@router.post("/register", response_model=Token)
async def register(user: UserRegister):
    """
    Register new user
    
    For MVP, stores in memory. Phase 4.5 will add database.
    """
    if user.email in fake_users_db:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Store user with hashed password
    fake_users_db[user.email] = {
        "email": user.email,
        "hashed_password": hash_password(user.password),
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Create token
    access_token = create_access_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        user_id=user.email
    )


@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """Login existing user"""
    db_user = fake_users_db.get(user.email)
    
    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    if not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        user_id=user.email
    )


@router.get("/me")
async def get_me(user_id: str = Depends(get_current_user)):
    """Get current user info"""
    user = fake_users_db.get(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "email": user["email"],
        "created_at": user["created_at"]
    }