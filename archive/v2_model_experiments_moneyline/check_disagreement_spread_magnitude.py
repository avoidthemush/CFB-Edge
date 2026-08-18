"""
Tests the hypothesis: spread/moneyline direction disagreements cluster
specifically at small |spread_open| values (near pick'em), which would
suggest a real market phenomenon (two markets, slightly different
pricing near even odds) rather than a data error.
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([df, df_2025], ignore_index=True)
full_df = full_df[
    full_df["market_spread_open"].notna() &
    full_df["market_home_moneyline"].notna() &
    full_df["market_away_moneyline"].notna()
].copy()

full_df["spread_says_home_favored"] = full_df["market_spread_open"] < 0
full_df["ml_says_home_favored"] = full_df["market_home_moneyline"] < 0
full_df["directions_agree"] = full_df["spread_says_home_favored"] == full_df["ml_says_home_favored"]
full_df["abs_spread"] = full_df["market_spread_open"].abs()

print("=== Disagreement rate by spread size bucket ===")
buckets = [(0, 3, "0-3 (near pick'em)"), (3, 7, "3-7"), (7, 14, "7-14"), (14, 100, "14+")]
for low, high, label in buckets:
    bucket = full_df[(full_df["abs_spread"] >= low) & (full_df["abs_spread"] < high)]
    if len(bucket) == 0:
        continue
    disagree_rate = (~bucket["directions_agree"]).mean() * 100
    print(f"  {label}: {(~bucket['directions_agree']).sum()}/{len(bucket)} disagree ({disagree_rate:.1f}%)")