# NBA Parlay Analyzer

A statistical analysis tool for NBA player prop parlays using real game data, probability modeling, and responsible gambling features. Built as a demonstration of full-stack development, data engineering, and ethical software design.

## 🎯 Project Overview

This system analyzes NBA player performance to calculate probabilities for over/under betting propositions. It scrapes real game data, applies statistical modeling with actual variance calculations, and provides transparent win/loss tracking to show users the reality of betting outcomes.

**Key Design Principle:** This tool prioritizes user protection over engagement, with rate limiting and results tracking designed to prevent compulsive behavior rather than encourage it.

## 🏗️ Architecture

### Backend (Python/FastAPI)
- RESTful API with JWT authentication
- PostgreSQL database with normalized schema
- Statistical probability engine using scipy
- Rate limiting (5 analyses/day anonymous, 7 for registered users)
- 5-minute cooldowns between analyses

### Data Pipeline
- Web scraper for Basketball-Reference (1,300+ historical games)
- Real variance calculations from game logs
- Rolling averages and trend detection
- Player vs. team matchup analysis

### Database
- 30 NBA teams
- 654 active players
- 1,300 game logs from 20 elite players
- User accounts with hashed passwords
- API usage tracking
- Results history for transparency

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL 16+
- Virtual environment recommended

### Installation

1. **Clone repository**
```bash
git clone https://github.com/DrDraken01/nba-parlay-analyzer.git
cd nba-parlay-analyzer
