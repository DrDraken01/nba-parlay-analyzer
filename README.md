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
