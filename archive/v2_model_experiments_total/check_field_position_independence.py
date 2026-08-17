"""
Before spending a Phase 2 look at 2025 on field_position, checking
whether it's a genuinely distinct signal or just a proxy for overall
team quality (which could make this result an indirect echo of
something else, not a real standalone market inefficiency).
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df = df[df["season"] <= 2024].copy()
df["combined_field_position"] = df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]
df["combined_sp_rating"] = df["home_sp+_rating"] + df["away_sp+_rating"]
df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]

print("=== Correlation checks ===")
print(f"corr(field_position, combined SP+ rating): {df['combined_field_position'].corr(df['combined_sp_rating']):.3f}")
print(f"corr(field_position, combined pace): {df['combined_field_position'].corr(df['combined_pace']):.3f}")
print(f"corr(field_position, actual_total) direct: {df['combined_field_position'].corr(df['actual_total']):.3f}")

print("\n=== Sample size behind the strong 2024 result ===")
year_df = df[df["season"] == 2024]
print(f"Total 2024 games with valid field_position: {year_df['combined_field_position'].notna().sum()}")