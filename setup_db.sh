#!/bin/bash
psql nba_parlays << 'EOF'

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(3) UNIQUE NOT NULL,
    city VARCHAR(100) NOT NULL,
    conference VARCHAR(10) NOT NULL,
    division VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    position VARCHAR(10),
    basketball_reference_id VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    game_date DATE NOT NULL,
    home_team_id INTEGER REFERENCES teams(id) NOT NULL,
    away_team_id INTEGER REFERENCES teams(id) NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    season INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS player_game_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id) NOT NULL,
    game_id INTEGER REFERENCES games(id) NOT NULL,
    minutes DECIMAL(4,1),
    points INTEGER DEFAULT 0,
    rebounds INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    steals INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    three_pointers_made INTEGER DEFAULT 0,
    UNIQUE(player_id, game_id)
);

INSERT INTO teams (name, abbreviation, city, conference, division) VALUES
('Golden State Warriors', 'GSW', 'San Francisco', 'Western', 'Pacific'),
('Sacramento Kings', 'SAC', 'Sacramento', 'Western', 'Pacific'),
('Los Angeles Lakers', 'LAL', 'Los Angeles', 'Western', 'Pacific'),
('Boston Celtics', 'BOS', 'Boston', 'Eastern', 'Atlantic')
ON CONFLICT (abbreviation) DO NOTHING;

\echo '✅ Database setup complete!'
SELECT * FROM teams;

EOF
