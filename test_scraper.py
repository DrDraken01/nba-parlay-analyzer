import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Environment variables loaded:")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_HOST: {os.getenv('DB_HOST')}")

# Test imports
try:
    import psycopg2
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
    print("\n✅ All packages imported successfully!")
    
    # Test database connection
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', '5432')
    )
    print("✅ Database connection successful!")
    
    # Query teams
    cursor = conn.cursor()
    cursor.execute("SELECT name, abbreviation FROM teams;")
    teams = cursor.fetchall()
    print(f"\n📊 Found {len(teams)} teams in database:")
    for team in teams:
        print(f"  - {team[0]} ({team[1]})")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")