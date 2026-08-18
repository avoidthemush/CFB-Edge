"""
Tests whether the SIZE of the gap between spread-implied win probability
and the actual devigged moneyline probability (within the approved
Unranked Favorite Dog pool specifically) works as a confidence ranking -
a different signal than raw spread size, which showed no clean trend.
"""
import pandas as pd
from app.models_ml.moneyline.margin_to_probability import spread_to_implied_win_probability
from app.models_ml.moneyline.devig import devig_two_way

STAKE = 100
GAP_BUCKETS = [(0, 0.02, "0-2%"), (0.02, 0.04, "2-4%"), (0.04, 0.07, "4-7%"), (0.07, 100, "7%+")]


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

qualifying["spread_implied_home_prob"] = qualifying["market_spread_open"].apply(spread_to_implied_win_probability)
devig_results = qualifying.apply(lambda r: devig_two_way(r["market_home_moneyline"], r["market_away_moneyline"]), axis=1)
qualifying["ml_fair_home_prob"] = devig_results.apply(lambda x: x[0])

# Gap FROM THE DOG'S PERSPECTIVE: does the moneyline give the dog MORE
# credit than the spread implies? Bigger positive gap = moneyline more
# favorable to dog than the spread alone would suggest = stronger signal
qualifying["dog_spread_implied_prob"] = qualifying.apply(
    lambda r: 1 - r["spread_implied_home_prob"] if r["home_is_dog"] else r["spread_implied_home_prob"], axis=1
)
qualifying["dog_ml_fair_prob"] = qualifying.apply(
    lambda r: 1 - r["ml_fair_home_prob"] if r["home_is_dog"] else r["ml_fair_home_prob"], axis=1
)
qualifying["ml_gap"] = (qualifying["dog_ml_fair_prob"] - qualifying["dog_spread_implied_prob"]).abs()
qualifying = qualifying.dropna(subset=["ml_gap"])

print(f"Total qualifying pool with valid gap: {len(qualifying)}\n")
print("=== ROI by moneyline-vs-spread gap size ===")
for low, high, label in GAP_BUCKETS:
    bucket = qualifying[(qualifying["ml_gap"] >= low) & (qualifying["ml_gap"] < high)].copy()
    if len(bucket) == 0:
        continue
    bucket["profit"] = bucket.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
    win_rate = bucket["dog_won"].mean() * 100
    profit = bucket["profit"].sum()
    roi = profit / (len(bucket) * STAKE) * 100
    marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
    print(f"  {label}: n={len(bucket)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}")