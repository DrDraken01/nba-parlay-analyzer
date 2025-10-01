import pandas as pd

df = pd.read_csv('data/gamelogs_2024.csv')

# Filter out inactive
df = df[df['PTS'] != 'Inactive']
df['PTS'] = pd.to_numeric(df['PTS'], errors='coerce')
df = df.dropna(subset=['PTS'])

curry = df[df['player_name'] == 'Stephen Curry']

print(f"Total Curry games after cleaning: {len(curry)}")
print(f"\nPTS column type: {curry['PTS'].dtype}")
print(f"\nFirst 10 PTS values:")
print(curry['PTS'].head(10).tolist())
print(f"\nBasic stats:")
print(f"Mean: {curry['PTS'].mean()}")
print(f"Std: {curry['PTS'].std()}")
print(f"Min: {curry['PTS'].min()}")
print(f"Max: {curry['PTS'].max()}")

print(f"\nAny outliers > 100?")
print(curry[curry['PTS'] > 100][['Date', 'PTS', 'player_name']])