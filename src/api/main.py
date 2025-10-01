"""
Main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import auth, routes

app = FastAPI(
    title="NBA Parlay Analyzer API",
    description="Statistical analysis for NBA player prop parlays with responsible gambling features",
    version="1.0.0"
)

# CORS - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(routes.router, prefix="/api", tags=["Analysis"])


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "NBA Parlay Analyzer API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}