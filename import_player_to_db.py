import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def import_players_to_database():
    """Import scraped player data into the database."""
    
    # Read the CSV
    df = pd.read_csv('data/players_2024_25.csv')
    
    # Remove non-player rows
    df = df[df['Player'] != 'League Average']
    df = df[df['Team'].notna()]  # Remove rows with no team
    
    # Team abbreviation mapping
    team_mapping = {
        'CHO': 'CHA',
        'BRK': 'BKN', 
        'PHO': 'PHX'
    }
    df['Team'] = df['Team'].replace(team_mapping)
    
    # Skip players who played for multiple teams (2TM, 3TM)
    df = df[~df['Team'].isin(['2TM', '3TM'])]
    
    print(f"Found {len(df)} players to import")
    
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', '5432')
    )
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute(
                "SELECT id FROM teams WHERE abbreviation = %s",
                (row['Team'],)
            )
            team_result = cursor.fetchone()
            team_id = team_result[0] if team_result else None
            
            if not team_id:
                print(f"⚠️  No team found for {row['Team']} - skipping {row['Player']}")
                skipped += 1
                continue
            
            cursor.execute(
                "SELECT id FROM players WHERE name = %s AND team_id = %s",
                (row['Player'], team_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE players 
                    SET position = %s, is_active = TRUE
                    WHERE id = %s
                """, (row['Pos'], existing[0]))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO players (name, team_id, position, is_active)
                    VALUES (%s, %s, %s, TRUE)
                """, (row['Player'], team_id, row['Pos']))
                inserted += 1
                
        except Exception as e:
            print(f"Error processing {row['Player']}: {e}")
            skipped += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Import complete!")
    print(f"   📥 Inserted: {inserted} new players")
    print(f"   🔄 Updated: {updated} existing players")
    print(f"   ⏭️  Skipped: {skipped} players")

if __name__ == "__main__":
    import_players_to_database()