"""
Independence check for the two most sample-size-credible candidates
from the recheck: travel (all_games) and wind (favorite_home). Same
scrutiny applied to field_position - checking these aren't secretly
proxies for team quality or each other before considering a 2025 spend.
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df = df[df["season"] <= 2024].copy()
df["combined_travel"] = df["home_travel_distance"].fillna(0) + df["away_travel_distance"].fillna(0)
df["combined_sp_rating"] = df["home_sp+_rating"] + df["away_sp+_rating"]
df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
df["combined_field_position"] = df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]

print("=== Travel: correlation checks ===")
print(f"corr(travel, combined SP+ rating): {df['combined_travel'].corr(df['combined_sp_rating']):.3f}")
print(f"corr(travel, combined pace): {df['combined_travel'].corr(df['combined_pace']):.3f}")
print(f"corr(travel, combined field_position): {df['combined_travel'].corr(df['combined_field_position']):.3f}")
print(f"corr(travel, actual_total) direct: {df['combined_travel'].corr(df['actual_total']):.3f}")

print("\n=== Wind: correlation checks ===")
print(f"corr(wind, combined SP+ rating): {df['wind_mph'].corr(df['combined_sp_rating']):.3f}")
print(f"corr(wind, combined pace): {df['wind_mph'].corr(df['combined_pace']):.3f}")
print(f"corr(wind, actual_total) direct: {df['wind_mph'].corr(df['actual_total']):.3f}")

print("\n=== Sample sizes ===")
print(f"Games with valid travel data: {df['combined_travel'].notna().sum()}")
print(f"Games with valid wind data: {df['wind_mph'].notna().sum()}")
print(f"Games where market_spread_open < 0 (favorite_home filter pool): {(df['market_spread_open'] < 0).sum()}")