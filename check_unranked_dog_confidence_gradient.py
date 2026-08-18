"""
Checks whether ROI varies meaningfully WITHIN the approved system's
0-10 spread range - if smaller-spread dogs within this range are
reliably better than larger ones, spread size itself becomes a natural,
market-based confidence ranking (consistent with Type B philosophy -
NOT reaching back for our own classifier, which already hurt this
system when combined earlier tonight).
"""
import pandas as pd

STAKE = 100
FINE_BUCKETS = [(0, 2, "0-2"), (2, 4, "2-4"), (4, 6, "4-6"), (6, 8, "6-8"), (8, 10, "8-10")]


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
full_df = full_df[
    full_df["market_spread_open"].notna() & full_df["actual_spread"].notna() &
    full_df["market_home_moneyline"].notna() & full_df["market_away_moneyline"].notna()
].copy()
full_df = full_df[full_df["market_spread_open"] != 0]

full_df["home_is_dog"] = full_df["market_spread_open"] > 0
full_df["dog_spread_size"] = full_df["market_spread_open"].abs()
full_df["dog_ml"] = full_df.apply(lambda r: r["market_home_moneyline"] if r["home_is_dog"] else r["market_away_moneyline"], axis=1)
full_df["dog_won"] = full_df.apply(lambda r: (r["actual_spread"] > 0) if r["home_is_dog"] else (r["actual_spread"] < 0), axis=1)
full_df["favorite_is_ranked"] = full_df.apply(lambda r: r["away_is_ranked"] if r["home_is_dog"] else r["home_is_ranked"], axis=1)

qualifying = full_df[(full_df["dog_spread_size"] <= 10) & (full_df["favorite_is_ranked"] == 0)].copy()

print(f"Total qualifying pool: {len(qualifying)}\n")
print("=== ROI by spread-size sub-bucket within the approved system ===")
for low, high, label in FINE_BUCKETS:
    bucket = qualifying[(qualifying["dog_spread_size"] >= low) & (qualifying["dog_spread_size"] < high)].copy()
    if len(bucket) == 0:
        continue
    bucket["profit"] = bucket.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
    win_rate = bucket["dog_won"].mean() * 100
    profit = bucket["profit"].sum()
    roi = profit / (len(bucket) * STAKE) * 100
    marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
    print(f"  {label}: n={len(bucket)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}")