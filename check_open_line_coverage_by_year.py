import pandas as pd

df_train = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df_train, df_2025], ignore_index=True)

print(f"Total FBS rows: {len(full_df)}\n")

print(f"{'Season':<8}{'Total games':>14}{'Has market_spread':>20}{'Has market_spread_open':>25}")
for season in sorted(full_df["season"].unique()):
    season_df = full_df[full_df["season"] == season]
    total = len(season_df)
    has_close = season_df["market_spread"].notna().sum()
    has_open = season_df["market_spread_open"].notna().sum()
    print(f"{season:<8}{total:>14}{has_close:>20}{has_open:>25}")

# Also check which providers are behind the low-open years
print("\n=== Provider breakdown for a low-open-coverage year, if any ===")
print(full_df.groupby("season")["market_provider"].value_counts())