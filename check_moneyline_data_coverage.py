"""
First real look at our moneyline data - never used in any model yet.
Checking coverage (do we have it for the years we need) and format
(American odds, as expected) before building anything on top of it.
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)

print(f"{'Year':<6}{'Total games':>14}{'Has home_moneyline':>20}{'Has away_moneyline':>20}")
for year in sorted(full_df["season"].unique()):
    year_df = full_df[full_df["season"] == year]
    total = len(year_df)
    has_home = year_df["market_home_moneyline"].notna().sum()
    has_away = year_df["market_away_moneyline"].notna().sum()
    print(f"{year:<6}{total:>14}{has_home:>20}{has_away:>20}")

print("\n=== Sample values (2024, home favorites vs underdogs) ===")
sample = full_df[(full_df["season"] == 2024) & full_df["market_home_moneyline"].notna()].head(10)
for _, row in sample.iterrows():
    print(f"  spread_open={row['market_spread_open']}, home_ml={row['market_home_moneyline']}, "
          f"away_ml={row['market_away_moneyline']}")