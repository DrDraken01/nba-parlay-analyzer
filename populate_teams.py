import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# All 30 NBA teams with proper data
NBA_TEAMS = [
    # Eastern Conference - Atlantic Division
    ('Boston Celtics', 'BOS', 'Boston', 'Eastern', 'Atlantic'),
    ('Brooklyn Nets', 'BKN', 'Brooklyn', 'Eastern', 'Atlantic'),
    ('New York Knicks', 'NYK', 'New York', 'Eastern', 'Atlantic'),
    ('Philadelphia 76ers', 'PHI', 'Philadelphia', 'Eastern', 'Atlantic'),
    ('Toronto Raptors', 'TOR', 'Toronto', 'Eastern', 'Atlantic'),
    
    # Eastern Conference - Central Division
    ('Chicago Bulls', 'CHI', 'Chicago', 'Eastern', 'Central'),
    ('Cleveland Cavaliers', 'CLE', 'Cleveland', 'Eastern', 'Central'),
    ('Detroit Pistons', 'DET', 'Detroit', 'Eastern', 'Central'),
    ('Indiana Pacers', 'IND', 'Indiana', 'Eastern', 'Central'),
    ('Milwaukee Bucks', 'MIL', 'Milwaukee', 'Eastern', 'Central'),
    
    # Eastern Conference - Southeast Division
    ('Atlanta Hawks', 'ATL', 'Atlanta', 'Eastern', 'Southeast'),
    ('Charlotte Hornets', 'CHA', 'Charlotte', 'Eastern', 'Southeast'),
    ('Miami Heat', 'MIA', 'Miami', 'Eastern', 'Southeast'),
    ('Orlando Magic', 'ORL', 'Orlando', 'Eastern', 'Southeast'),
    ('Washington Wizards', 'WAS', 'Washington', 'Eastern', 'Southeast'),
    
    # Western Conference - Northwest Division
    ('Denver Nuggets', 'DEN', 'Denver', 'Western', 'Northwest'),
    ('Minnesota Timberwolves', 'MIN', 'Minnesota', 'Western', 'Northwest'),
    ('Oklahoma City Thunder', 'OKC', 'Oklahoma City', 'Western', 'Northwest'),
    ('Portland Trail Blazers', 'POR', 'Portland', 'Western', 'Northwest'),
    ('Utah Jazz', 'UTA', 'Utah', 'Western', 'Northwest'),
    
    # Western Conference - Pacific Division
    ('Golden State Warriors', 'GSW', 'San Francisco', 'Western', 'Pacific'),
    ('Los Angeles Clippers', 'LAC', 'Los Angeles', 'Western', 'Pacific'),
    ('Los Angeles Lakers', 'LAL', 'Los Angeles', 'Western', 'Pacific'),
    ('Phoenix Suns', 'PHX', 'Phoenix', 'Western', 'Pacific'),
    ('Sacramento Kings', 'SAC', 'Sacramento', 'Western', 'Pacific'),
    
    # Western Conference - Southwest Division
    ('Dallas Mavericks', 'DAL', 'Dallas', 'Western', 'Southwest'),
    ('Houston Rockets', 'HOU', 'Houston', 'Western', 'Southwest'),
    ('Memphis Grizzlies', 'MEM', 'Memphis', 'Western', 'Southwest'),
    ('New Orleans Pelicans', 'NOP', 'New Orleans', 'Western', 'Southwest'),
    ('San Antonio Spurs', 'SAS', 'San Antonio', 'Western', 'Southwest'),
]

def populate_teams():
    """Insert all 30 NBA teams into the database."""
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', '5432')
    )
    
    cursor = conn.cursor()
    
    try:
        # Insert all teams
        for team in NBA_TEAMS:
            cursor.execute("""
                INSERT INTO teams (name, abbreviation, city, conference, division)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (abbreviation) DO UPDATE 
                SET name = EXCLUDED.name,
                    city = EXCLUDED.city,
                    conference = EXCLUDED.conference,
                    division = EXCLUDED.division
            """, team)
        
        conn.commit()
        print(f"✅ Successfully inserted/updated {len(NBA_TEAMS)} teams!")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM teams;")
        count = cursor.fetchone()[0]
        print(f"📊 Total teams in database: {count}")
        
        # Show all teams
        cursor.execute("""
            SELECT abbreviation, name, conference 
            FROM teams 
            ORDER BY conference, division, name
        """)
        teams = cursor.fetchall()
        
        print("\n🏀 All NBA Teams:")
        print("-" * 60)
        current_conf = None
        for abbr, name, conf in teams:
            if conf != current_conf:
                print(f"\n{conf} Conference:")
                current_conf = conf
            print(f"  {abbr:4} - {name}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    populate_teams()