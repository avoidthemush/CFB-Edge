"""
Investigates whether 2025 has some systemic characteristic that would
explain why all 4 approved Total systems (Pace, Field Position, Travel,
Wind Deviation) soften in that specific year, despite being confirmed
independent of each other. Checking real, concrete possibilities:
market behavior shift, data completeness, and whether the softening is
correlated across systems on the SAME GAMES (shared cause) or scattered
across different games (coincidental).
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)
full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]

print("=== Market total-setting behavior, by year ===")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    avg_total = year_df["market_total_open"].mean()
    std_total = year_df["market_total_open"].std()
    market_mae = (year_df["actual_total"] - year_df["market_total_open"]).abs().mean()
    print(f"{year}: avg market total={avg_total:.1f}, std={std_total:.1f}, market MAE={market_mae:.2f}")

print("\n=== Data completeness by year (any degradation in 2025 specifically?) ===")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    total = len(year_df)
    has_travel = (year_df["home_travel_distance"].notna() & year_df["away_travel_distance"].notna()).mean() * 100
    has_wind = year_df["wind_mph"].notna().mean() * 100
    has_field_pos = year_df["home_off_field_position_predicted_points"].notna().mean() * 100
    has_pace = year_df["home_off_plays_per_drive"].notna().mean() * 100
    print(f"{year}: n={total}, travel={has_travel:.1f}%, wind={has_wind:.1f}%, "
          f"field_pos={has_field_pos:.1f}%, pace={has_pace:.1f}%")

print("\n=== Provider mix by year (did the market source itself change?) ===")
for year in [2022, 2023, 2024, 2025]:
    year_df = full_df[full_df["season"] == year]
    print(f"{year}:")
    print(year_df["market_provider"].value_counts().to_string())