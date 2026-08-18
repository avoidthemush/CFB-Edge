"""
Calibrates the real standard deviation of (actual margin vs. spread-
implied margin) from OUR OWN completed FBS games, rather than trusting
the literature's wide range (15-21, per research) blindly. This number
directly determines how we convert a spread into a win probability -
getting it wrong would systematically bias every Moneyline calculation
downstream.
"""
import numpy as np
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)
full_df = full_df[full_df["market_spread_open"].notna() & full_df["actual_spread"].notna()].copy()

# spread_open is from the HOME team's perspective in our data (negative = home favored)
# actual_spread = home_points - away_points (positive = home won by that much)
# spread-implied margin for home team = -spread_open
full_df["spread_implied_margin"] = -full_df["market_spread_open"]
full_df["residual"] = full_df["actual_spread"] - full_df["spread_implied_margin"]

print(f"Total games: {len(full_df)}\n")
print("=== Residual (actual margin vs. spread-implied margin) stats, by year ===")
for year in sorted(full_df["season"].unique()):
    year_df = full_df[full_df["season"] == year]
    print(f"  {year}: mean={year_df['residual'].mean():+.2f}, std={year_df['residual'].std():.2f}, n={len(year_df)}")

print(f"\n=== POOLED across all years (2021-2025) ===")
print(f"  Mean residual: {full_df['residual'].mean():+.3f} (should be near 0 if spreads are well-calibrated on average)")
print(f"  Std dev: {full_df['residual'].std():.2f}")
print(f"\nFor comparison, literature range for CFB: 15-21 (NFL is ~13.5-14, CFB wider due to more blowouts/upsets)")