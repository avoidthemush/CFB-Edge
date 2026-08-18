"""
Checks whether market_spread_open and market_home_moneyline/
market_away_moneyline agree on basic DIRECTION (who's favored) across
the full dataset - a real inconsistency was spotted in a manual sample
(spread said home favored by 4.5, but home_ml was +175, an underdog
price). Before building any Moneyline model, need to know if this is
an isolated glitch or a systematic data problem.
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)
full_df = full_df[
    full_df["market_spread_open"].notna() &
    full_df["market_home_moneyline"].notna() &
    full_df["market_away_moneyline"].notna()
].copy()

# Direction implied by spread: negative = home favored
full_df["spread_says_home_favored"] = full_df["market_spread_open"] < 0
# Direction implied by moneyline: negative ML = favored
full_df["ml_says_home_favored"] = full_df["market_home_moneyline"] < 0

full_df["directions_agree"] = full_df["spread_says_home_favored"] == full_df["ml_says_home_favored"]

print(f"Total games checked: {len(full_df)}")
print(f"Directions agree: {full_df['directions_agree'].sum()} ({full_df['directions_agree'].mean()*100:.1f}%)")
print(f"Directions DISAGREE: {(~full_df['directions_agree']).sum()} ({(~full_df['directions_agree']).mean()*100:.1f}%)")

print("\n=== By year ===")
for year in sorted(full_df["season"].unique()):
    year_df = full_df[full_df["season"] == year]
    disagree = (~year_df["directions_agree"]).sum()
    print(f"  {year}: {disagree}/{len(year_df)} disagree ({disagree/len(year_df)*100:.1f}%)")

print("\n=== Sample of disagreeing rows ===")
disagreements = full_df[~full_df["directions_agree"]].head(10)
for _, row in disagreements.iterrows():
    print(f"  season={row['season']}, spread_open={row['market_spread_open']}, "
          f"home_ml={row['market_home_moneyline']}, away_ml={row['market_away_moneyline']}")