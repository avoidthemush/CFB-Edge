"""
Investigates what's actually different about 2022 and 2025 (both failed)
versus 2023-2024 (both worked) - four separate modeling approaches all
showing this exact same split can't be coincidence. Checking data
completeness, scoring levels, and market behavior year by year.
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)
full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]

print(f"{'Year':<6}{'Games':>8}{'Avg Total':>12}{'Avg Market Open':>18}{'Avg |Total-Open|':>18}{'Has weather %':>15}{'Has pace %':>12}")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    avg_total = year_df["actual_total"].mean()
    avg_open = year_df["market_total_open"].mean()
    avg_gap = (year_df["actual_total"] - year_df["market_total_open"]).abs().mean()
    has_weather = year_df["wind_mph"].notna().mean() * 100
    has_pace = (year_df["home_off_plays_per_drive"].notna() & year_df["away_off_plays_per_drive"].notna()).mean() * 100
    print(f"{year:<6}{len(year_df):>8}{avg_total:>12.1f}{avg_open:>18.1f}{avg_gap:>18.1f}{has_weather:>15.1f}{has_pace:>12.1f}")