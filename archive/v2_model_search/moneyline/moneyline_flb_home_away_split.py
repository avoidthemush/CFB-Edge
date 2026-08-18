"""
Splits the FLB spread-bucket test by home dog vs away dog - testing
whether public bettors' well-documented lean toward the home team
creates an asymmetry in how the favorite-longshot bias shows up.
"""
import pandas as pd

STAKE = 100
SPREAD_BUCKETS = [
    (0, 3, "0-3"), (3, 7, "3-7"), (7, 10, "7-10"),
    (10, 14, "10-14"), (14, 21, "14-21"), (21, 100, "21+"),
]


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


def run():
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

    for dog_type, label in [(True, "HOME dogs"), (False, "AWAY dogs")]:
        print(f"\n=== {label} ===")
        subset = full_df[full_df["home_is_dog"] == dog_type]
        for low, high, blabel in SPREAD_BUCKETS:
            bucket = subset[(subset["dog_spread_size"] >= low) & (subset["dog_spread_size"] < high)].copy()
            if len(bucket) == 0:
                continue
            bucket["profit"] = bucket.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
            win_rate = bucket["dog_won"].mean() * 100
            profit = bucket["profit"].sum()
            roi = profit / (len(bucket) * STAKE) * 100
            marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
            print(f"  {blabel}: n={len(bucket)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}")


if __name__ == "__main__":
    run()