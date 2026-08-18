"""
Final statistical confirmation for the ranked-favorite finding - the
cleanest result of the night (5/5 years profitable both directions).
Bootstrap resampling on ROI to confirm this isn't a lucky aggregate.
"""
import numpy as np
import pandas as pd

STAKE = 100
MAX_DOG_SPREAD = 10
N_BOOTSTRAP = 10000


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
    full_df["favorite_is_ranked"] = full_df.apply(lambda r: r["away_is_ranked"] if r["home_is_dog"] else r["home_is_ranked"], axis=1)

    dog_pool = full_df[(full_df["dog_spread_size"] <= MAX_DOG_SPREAD) & (full_df["favorite_is_ranked"] == 0)].copy()
    dog_pool["profit"] = dog_pool.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)

    n = len(dog_pool)
    total_profit = dog_pool["profit"].sum()
    roi = total_profit / (n * STAKE) * 100
    print(f"Total bets: {n}, Total profit: ${total_profit:+.0f}, ROI: {roi:+.1f}%\n")

    profits = dog_pool["profit"].values
    rng = np.random.default_rng(42)
    bootstrap_rois = np.array([
        rng.choice(profits, size=n, replace=True).sum() / (n * STAKE) * 100
        for _ in range(N_BOOTSTRAP)
    ])
    pct_profitable = (bootstrap_rois > 0).mean() * 100
    ci_low, ci_high = np.percentile(bootstrap_rois, [2.5, 97.5])
    print(f"Bootstrap: {pct_profitable:.1f}% of resamples profitable, 95% CI [{ci_low:+.1f}%, {ci_high:+.1f}%]")


if __name__ == "__main__":
    run()