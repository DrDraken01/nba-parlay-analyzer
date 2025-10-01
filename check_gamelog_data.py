import pandas as pd

df = pd.read_csv('data/gamelogs_2024.csv')

print("First few rows for Curry:")
curry = df[df['player_name'] == 'Stephen Curry'].head(10)
print(curry[['Date', 'PTS', 'AST', 'TRB', 'player_name']])

print("\nData types:")
print(df[['PTS', 'AST', 'TRB']].dtypes)

print("\nSample PTS values:")
print(df['PTS'].head(20))

print("\nAny non-numeric values?")
print(df['PTS'].apply(lambda x: type(x).__name__).value_counts())