"""
Estimates real weekly volume for the approved Unranked Favorite Dog
system - how many games per week actually qualify, on average.
"""
import pandas as pd

full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
full_df = full_df[
    full_df["market_spread_open"].notna() & full_df["market_home_moneyline"].notna()
].copy()
full_df = full_df[full_df["market_spread_open"] != 0]

full_df["home_is_dog"] = full_df["market_spread_open"] > 0
full_df["dog_spread_size"] = full_df["market_spread_open"].abs()
full_df["favorite_is_ranked"] = full_df.apply(
    lambda r: r["away_is_ranked"] if r["home_is_dog"] else r["home_is_ranked"], axis=1
)

qualifying = full_df[(full_df["dog_spread_size"] <= 10) & (full_df["favorite_is_ranked"] == 0)]

print(f"Total qualifying games across all years: {len(qualifying)}\n")
print("=== Qualifying games per week, by season (weeks 1-15) ===")
weekly_counts = qualifying.groupby(["season", "week"]).size()
avg_by_week = weekly_counts.groupby("week").mean()
for week in sorted(avg_by_week.index):
    if week <= 15:
        print(f"  Week {week}: avg {avg_by_week[week]:.1f} qualifying games")

print(f"\nOverall average per week (weeks 1-15): {avg_by_week[avg_by_week.index <= 15].mean():.1f}")