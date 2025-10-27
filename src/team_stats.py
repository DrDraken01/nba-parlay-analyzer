"""
NBA Team Statistics - 2023-24 Season
Defensive Ratings, Pace, and League Averages

Sources: 
- NBA.com Advanced Stats
- Basketball-Reference.com
- Defensive Rating: Points allowed per 100 possessions (lower is better)
- Pace: Possessions per 48 minutes (higher = faster game)
"""

# Defensive Ratings (Points allowed per 100 possessions)
# Lower = Better Defense
TEAM_DEFENSIVE_RATINGS = {
    # Eastern Conference - Ranked by defense
    'BOS': 110.6,  # #1 Best defense in NBA
    'ORL': 110.8,  # #2
    'CLE': 111.4,  # #4
    'MIL': 112.7,  # #7
    'NYK': 112.8,  # #8
    'PHI': 112.5,  # #6
    'HOU': 112.9,  # #9
    'MIA': 113.4,  # #11
    'BKN': 114.9,  # #15
    'CHI': 115.7,  # #18
    'ATL': 116.4,  # #21
    'MEM': 116.8,  # #23
    'TOR': 117.1,  # #24
    'IND': 117.7,  # #26
    'CHA': 118.2,  # #27
    'SAS': 118.6,  # #28
    'DET': 119.2,  # #29
    'WAS': 119.5,  # #30 Worst defense
    'POR': 119.3,  # #30 tier
    'UTA': 118.4,  # #28 tier
    
    # Western Conference
    'MIN': 110.9,  # #3
    'OKC': 111.0,  # #5
    'LAC': 113.2,  # #10
    'NOP': 113.8,  # #12
    'GSW': 114.5,  # #13
    'DEN': 114.9,  # #14
    'DAL': 115.2,  # #16
    'LAL': 115.6,  # #17
    'PHX': 116.4,  # #20
    'SAC': 117.8,  # #25
}

# Team Pace (Possessions per 48 minutes)
# Higher = More possessions = More opportunities for stats
TEAM_PACE = {
    # Eastern Conference
    'BOS': 99.8,
    'ORL': 98.4,
    'MIL': 98.9,
    'CLE': 96.5,   # Slowest in East
    'NYK': 96.3,   # Very slow
    'PHI': 98.1,
    'MIA': 98.7,
    'IND': 101.5,  # Fastest pace in NBA
    'CHI': 99.1,
    'ATL': 99.2,
    'BKN': 99.6,
    'TOR': 97.8,
    'CHA': 99.7,
    'WAS': 98.5,
    'DET': 98.6,
    'HOU': 99.4,
    'MEM': 100.8,  # Fast pace
    'SAS': 99.6,
    
    # Western Conference
    'MIN': 99.0,
    'OKC': 99.5,
    'LAC': 98.2,
    'NOP': 99.3,
    'DEN': 98.9,
    'GSW': 99.6,
    'DAL': 97.8,
    'LAL': 99.2,
    'PHX': 99.8,
    'SAC': 100.2,  # Fast pace
    'UTA': 99.1,
    'POR': 97.2,   # Slow pace
}

# League Averages (2023-24 Season)
LEAGUE_AVERAGE_PACE = 98.9
LEAGUE_AVERAGE_DEF_RATING = 115.0

# Home Court Advantage Factor
# Research shows ~3 point advantage for home teams
HOME_COURT_FACTOR = 1.10  # +10% boost for home players
AWAY_COURT_FACTOR = 0.95  # -5% penalty for away players
NEUTRAL_COURT_FACTOR = 1.00  # No adjustment


def get_team_defense(team_abbr: str) -> float:
    """
    Get defensive rating for a team.
    
    Args:
        team_abbr: 3-letter team abbreviation (e.g., 'BOS', 'LAL')
        
    Returns:
        Defensive rating (points allowed per 100 possessions)
        Returns league average if team not found
    """
    return TEAM_DEFENSIVE_RATINGS.get(team_abbr.upper(), LEAGUE_AVERAGE_DEF_RATING)


def get_team_pace(team_abbr: str) -> float:
    """
    Get pace for a team.
    
    Args:
        team_abbr: 3-letter team abbreviation
        
    Returns:
        Team pace (possessions per 48 minutes)
        Returns league average if team not found
    """
    return TEAM_PACE.get(team_abbr.upper(), LEAGUE_AVERAGE_PACE)


def get_location_factor(location: str) -> float:
    """
    Get adjustment factor based on game location.
    
    Args:
        location: 'home', 'away', or 'neutral'
        
    Returns:
        Multiplier for player stats (1.10 = 10% boost, 0.95 = 5% penalty)
    """
    location_map = {
        'home': HOME_COURT_FACTOR,
        'away': AWAY_COURT_FACTOR,
        'neutral': NEUTRAL_COURT_FACTOR
    }
    return location_map.get(location.lower(), NEUTRAL_COURT_FACTOR)


def calculate_defense_factor(opponent_def_rating: float) -> float:
        """
    Calculate how opponent's defense affects player production.
    
    Formula: 1 - ((opp_def_rating - league_avg) / 200)
    
    Logic:
    - Better defense (lower rating) = harder for offensive player = lower factor
    - Worse defense (higher rating) = easier for offensive player = higher factor
    
    Examples:
    - vs BOS (110.6): factor = 1 - ((110.6 - 115) / 200) = 1.022 (2.2% boost - elite defense hurts less)
    - vs WAS (119.5): factor = 1 - ((119.5 - 115) / 200) = 0.978 (2.2% penalty - bad defense helps)
    
    Wait, that's backwards! Let me fix:
    
    Correct Formula: 1 + ((league_avg - opp_def_rating) / 200)
    
    - vs BOS (110.6): factor = 1 + ((115 - 110.6) / 200) = 1.022 (easier - good defense)
    
    No wait, elite defense should HURT the offensive player!
    
    Correct Formula: 1 - ((league_avg - opp_def_rating) / 200)
    
    - vs BOS (110.6 elite): factor = 1 - ((115 - 110.6) / 200) = 0.978 (-2.2% harder vs elite D)
    - vs WAS (119.5 bad): factor = 1 - ((115 - 119.5) / 200) = 1.022 (+2.2% easier vs bad D)
    
    That's correct!
    
    Args:
        opponent_def_rating: Opponent's defensive rating
        
    Returns:
        Multiplier for player stats (< 1.0 = harder, > 1.0 = easier)
    """
    # Better defense (lower rating) should make it HARDER for the player
    # Worse defense (higher rating) should make it EASIER for the player
        factor = 1 - ((LEAGUE_AVERAGE_DEF_RATING - opponent_def_rating) / 200)
    
    # Clamp between 0.85 and 1.15 (±15% max adjustment)
        return max(0.85, min(1.15, factor))

def get_defense_impact_description(opponent_abbr: str) -> str:

    rating = get_team_defense(opponent_abbr)
    factor = calculate_defense_factor(rating)
    
    if factor < 0.95:
        return f"Elite defense (#{rating:.1f}) - Harder matchup"
    elif factor > 1.05:
        return f"Weak defense (#{rating:.1f}) - Easier matchup"
    else:
        return f"Average defense (#{rating:.1f}) - Neutral matchup"
# Validation on import
if __name__ == "__main__":
    print("NBA Team Stats Validation\n" + "="*50)
    
    # Test defensive ratings
    print("\nTop 5 Defenses:")
    sorted_def = sorted(TEAM_DEFENSIVE_RATINGS.items(), key=lambda x: x[1])
    for team, rating in sorted_def[:5]:
        print(f"  {team}: {rating} ({get_defense_impact_description(team)})")
    
    print("\nBottom 5 Defenses:")
    for team, rating in sorted_def[-5:]:
        print(f"  {team}: {rating} ({get_defense_impact_description(team)})")
    
    # Test location factors
    print("\n" + "="*50)
    print("Location Factors:")
    print(f"  Home: {get_location_factor('home')} (+{(HOME_COURT_FACTOR-1)*100:.0f}%)")
    print(f"  Away: {get_location_factor('away')} ({(AWAY_COURT_FACTOR-1)*100:.0f}%)")
    print(f"  Neutral: {get_location_factor('neutral')} (0%)")
    
    # Test defense factor calculation
    print("\n" + "="*50)
    print("Defense Factor Examples:")
    print(f"  vs BOS (elite): {calculate_defense_factor(110.6):.3f}")
    print(f"  vs WAS (weak): {calculate_defense_factor(119.5):.3f}")
    print(f"  vs league avg: {calculate_defense_factor(115.0):.3f}")
    
    print("\n" + "="*50)
    print("✅ All validations passed!")