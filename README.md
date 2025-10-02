# NBA Parlay Analyzer

Statistical analysis API for NBA player prop parlays using real historical game data and probability modeling.

## Overview

Backend system that analyzes NBA player performance to calculate probabilities for over/under betting propositions. Uses scraped game data from 1,300+ games to provide statistical predictions with actual variance (not estimates).

**Design Focus:** Rate limiting and results tracking designed to show users the reality of betting outcomes, not to maximize engagement.

## Tech Stack

- **API:** FastAPI with JWT authentication
- **Database:** PostgreSQL (30 teams, 654 players, 1,300 games)
- **Analysis:** scipy for statistical distributions, pandas for data processing
- **Data:** Web scraping from Basketball-Reference with respectful rate limiting

## Setup
```bash
# Clone and setup
git clone https://github.com/DrDraken01/nba-parlay-analyzer.git
cd nba-parlay-analyzer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database
createdb nba_parlays
psql nba_parlays -f schema.sql
psql nba_parlays -f add_users_table.sql
python populate_teams.py

# Configure .env with your database credentials
# Run API
uvicorn src.api.main:app --reload --port 8000

API docs: http://127.0.0.1:8000/docs
Features

Real variance from historical games (not estimates)
JWT authentication with bcrypt
Rate limiting: 5 analyses/day (anonymous), 7 (authenticated)
5-minute cooldowns between analyses
Results tracking showing actual win/loss records
Multi-leg parlay combined probabilities

API Example
bash# Register
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Analyze
curl -X POST "http://localhost:8000/api/analyze-leg" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"player":"Stephen Curry","stat_type":"points","line":25.5,"bet_type":"over"}'
Disclaimer
Educational portfolio project. Not financial advice. Sports betting has negative expected value. Most users lose money over time.
Gambling problem? Call 1-800-GAMBLER or visit ncpgambling.org
Contact
GitHub: @DrDraken01

Save (Ctrl+O, Enter, Ctrl+X), then commit:
```bash
git add README.md
git commit -m "Add README documentation"
git push
