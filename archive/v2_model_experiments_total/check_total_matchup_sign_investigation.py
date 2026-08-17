"""
Investigates WHY combined_matchup_scoring_potential shows negative
(favors UNDER) in the trained model despite a positive raw correlation
- checking whether high-matchup-potential games are disproportionately
blowouts (garbage-time suppression theory) before trusting this enough
to spend a Phase 2 look at 2025.
"""
import pandas as pd
import numpy as np

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df = df[df["season"] <= 2024].copy()
df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()

df["home_matchup_scoring_potential"] = df["matchup_home_pass_off_vs_away_pass_def"] + df["matchup_home_rush_off_vs_away_rush_def"]
df["away_matchup_scoring_potential"] = df["matchup_away_pass_off_vs_home_pass_def"] + df["matchup_away_rush_off_vs_home_rush_def"]
df["combined_matchup_scoring_potential"] = df["home_matchup_scoring_potential"] + df["away_matchup_scoring_potential"]
df["margin_abs"] = df["actual_spread"].abs()  # computed BEFORE slicing, fixes the earlier bug

print("=== Correlation check ===")
print(f"corr(combined_matchup_scoring_potential, wind_mph): {df['combined_matchup_scoring_potential'].corr(df['wind_mph']):.3f}")
print(f"corr(combined_matchup_scoring_potential, actual_total) DIRECTLY: {df['combined_matchup_scoring_potential'].corr(df['actual_total']):.3f}")
print(f"corr(combined_matchup_scoring_potential, margin_abs): {df['combined_matchup_scoring_potential'].corr(df['margin_abs']):.3f}")
print(f"corr(combined_matchup_scoring_potential, combined_pace) [multicollinearity check]: "
      f"{df['combined_matchup_scoring_potential'].corr(df['home_off_plays_per_drive'] + df['away_off_plays_per_drive']):.3f}")

median_val = df["combined_matchup_scoring_potential"].median()
high = df[df["combined_matchup_scoring_potential"] > median_val].copy()
low = df[df["combined_matchup_scoring_potential"] <= median_val].copy()

print("\n=== High vs low matchup potential ===")
print(f"High matchup potential (n={len(high)}): avg actual_total = {high['actual_total'].mean():.1f}, "
      f"avg margin = {high['margin_abs'].mean():.1f}")
print(f"Low matchup potential (n={len(low)}): avg actual_total = {low['actual_total'].mean():.1f}, "
      f"avg margin = {low['margin_abs'].mean():.1f}")

print("\n=== Blowout check: is high matchup potential specifically associated with the BIGGEST margins? ===")
blowouts = df[df["margin_abs"] >= 28]  # roughly top quartile of margin size
close_games = df[df["margin_abs"] < 10]
print(f"Blowout games (margin>=28, n={len(blowouts)}): avg matchup potential = {blowouts['combined_matchup_scoring_potential'].mean():.3f}")
print(f"Close games (margin<10, n={len(close_games)}): avg matchup potential = {close_games['combined_matchup_scoring_potential'].mean():.3f}")

print("\n=== Does total scoring drop in blowouts specifically? ===")
print(f"Blowout games avg actual_total: {blowouts['actual_total'].mean():.1f}")
print(f"Close games avg actual_total: {close_games['actual_total'].mean():.1f}")