"""
Real statistical diagnosis of why every Total approach fails specifically
on 2022 and 2025 - checking VARIANCE (not just mean, already ruled out
flat) and whether the actual mathematical relationship between our
strongest predictors and actual_total is stable or shifts by year.
"""
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)
full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()].copy()
full_df["combined_pace"] = full_df["home_off_plays_per_drive"] + full_df["away_off_plays_per_drive"]

print(f"{'Year':<6}{'Std Dev Total':>16}{'Var Total':>14}{'Skew':>10}")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    std = year_df["actual_total"].std()
    var = year_df["actual_total"].var()
    skew = stats.skew(year_df["actual_total"].dropna())
    print(f"{year:<6}{std:>16.2f}{var:>14.1f}{skew:>10.3f}")

print(f"\n{'Year':<6}{'corr(pace, total)':>20}{'corr(wind, total)':>20}{'corr(pace, gap-to-market)':>28}")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    corr_pace = year_df["combined_pace"].corr(year_df["actual_total"])
    corr_wind = year_df["wind_mph"].corr(year_df["actual_total"])
    market_error = year_df["actual_total"] - year_df["market_total_open"]
    corr_pace_gap = year_df["combined_pace"].corr(market_error)
    print(f"{year:<6}{corr_pace:>20.3f}{corr_wind:>20.3f}{corr_pace_gap:>28.3f}")

print("\n=== Market's OWN accuracy by year (MAE of market_total_open vs actual) ===")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    market_mae = (year_df["actual_total"] - year_df["market_total_open"]).abs().mean()
    print(f"  {year}: market MAE = {market_mae:.2f}")