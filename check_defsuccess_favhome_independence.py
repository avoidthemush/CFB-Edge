"""
Independence check for the two credible-sample-size survivors:
def_success_allowed (low_wind) and favorite_home standalone (largest
sample of any candidate tested, ~148-149 games/year).
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df = df[df["season"] <= 2024].copy()
df["combined_def_success_allowed"] = df["home_def_success_rate_allowed"] + df["away_def_success_rate_allowed"]
df["combined_sp_rating"] = df["home_sp+_rating"] + df["away_sp+_rating"]
df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
df["combined_field_position"] = df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]
df["combined_travel"] = df["home_travel_distance"].fillna(0) + df["away_travel_distance"].fillna(0)

print("=== def_success_allowed: correlation checks ===")
print(f"corr(def_success_allowed, combined SP+): {df['combined_def_success_allowed'].corr(df['combined_sp_rating']):.3f}")
print(f"corr(def_success_allowed, combined pace): {df['combined_def_success_allowed'].corr(df['combined_pace']):.3f}")
print(f"corr(def_success_allowed, actual_total) direct: {df['combined_def_success_allowed'].corr(df['actual_total']):.3f}")

print("\n=== favorite_home: what fraction of ALL games is this filter? ===")
fav_home_pct = (df["market_spread_open"] < 0).mean() * 100
print(f"Games where home is favorite: {fav_home_pct:.1f}% of all games")

print("\n=== Does home-favorite status correlate with pace/field_position/travel (already-approved buckets)? ===")
df["is_favorite_home"] = (df["market_spread_open"] < 0).astype(int)
print(f"corr(favorite_home, combined pace): {df['is_favorite_home'].corr(df['combined_pace']):.3f}")
print(f"corr(favorite_home, combined field_position): {df['is_favorite_home'].corr(df['combined_field_position']):.3f}")
print(f"corr(favorite_home, combined travel): {df['is_favorite_home'].corr(df['combined_travel']):.3f}")