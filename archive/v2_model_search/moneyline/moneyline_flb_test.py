"""
Direct, model-free test of the favorite-longshot bias literature:
blindly bet the underdog's moneyline in each spread-size bucket, no
model required - literally testing whether the MARKET ITSELF has a
predictable, exploitable bias, the purest form of Type B.

Research-grounded hypothesis: BIG underdogs should be bad value
(confirmed FLB - overpriced), SMALL/slight underdogs may be where the
value actually sits (per separate NFL/CFB research finding "slight
underdog bets appear to be the best option"). Testing across ALL years
we have (2021-2025) since this needs no training data of its own -
pure market-behavior observation, not a model to fit.
"""
import pandas as pd

STAKE = 100
SPREAD_BUCKETS = [
    (0, 3, "Pick'em/slight dog (0-3)"),
    (3, 7, "Small dog (3-7)"),
    (7, 10, "Modest dog (7-10)"),
    (10, 14, "Real dog (10-14)"),
    (14, 21, "Big dog (14-21)"),
    (21, 100, "Huge dog (21+)"),
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

    # Identify the underdog (positive spread side) and their moneyline/win status
    full_df["home_is_dog"] = full_df["market_spread_open"] > 0
    full_df["dog_spread_size"] = full_df["market_spread_open"].abs()
    full_df["dog_ml"] = full_df.apply(
        lambda r: r["market_home_moneyline"] if r["home_is_dog"] else r["market_away_moneyline"], axis=1
    )
    full_df["dog_won"] = full_df.apply(
        lambda r: (r["actual_spread"] > 0) if r["home_is_dog"] else (r["actual_spread"] < 0), axis=1
    )
    full_df = full_df[full_df["market_spread_open"] != 0]  # exclude true pick'em, no underdog

    print("=== BLIND underdog moneyline bet, by spread-size bucket, ALL YEARS POOLED (2021-2025) ===\n")
    for low, high, label in SPREAD_BUCKETS:
        bucket = full_df[(full_df["dog_spread_size"] >= low) & (full_df["dog_spread_size"] < high)].copy()
        if len(bucket) == 0:
            continue
        bucket["profit"] = bucket.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
        win_rate = bucket["dog_won"].mean() * 100
        total_profit = bucket["profit"].sum()
        roi = total_profit / (len(bucket) * STAKE) * 100
        avg_ml = bucket["dog_ml"].mean()
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"  {label}: n={len(bucket)}, win={win_rate:.1f}%, avg_ml={avg_ml:+.0f}, "
              f"${total_profit:+.0f} profit, ROI={roi:+.1f}%{marker}")

    print("\n=== Same breakdown, BY YEAR, for the most promising bucket(s) ===")


if __name__ == "__main__":
    run()