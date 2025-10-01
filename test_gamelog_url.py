import requests
from bs4 import BeautifulSoup

# Test if we can access Curry's 2024 game log
url = "https://www.basketball-reference.com/players/c/curryst01/gamelog/2024"

response = requests.get(url)
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Check what tables exist
    tables = soup.find_all('table')
    print(f"\nFound {len(tables)} tables")
    
    for i, table in enumerate(tables):
        table_id = table.get('id', 'no-id')
        print(f"  Table {i}: {table_id}")
    
    # Try to find the game log table
    gamelog = soup.find('table', {'id': 'pgl_basic'})
    if gamelog:
        print("\n✓ Found game log table!")
    else:
        print("\n✗ Game log table 'pgl_basic' not found")
        print("\nTrying alternate table names...")
        for table in tables:
            print(f"  {table.get('id')}")
else:
    print(f"Failed to fetch page: {response.status_code}")