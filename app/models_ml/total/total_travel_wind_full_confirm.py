"""
Phase 2 confirmation for travel and wind - both passed independence
checks (uncorrelated with existing signals) and independent-split
recheck (2023, 2024 both strong, credible sample sizes ~74-81 games/
year). Full test including 2025.
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest

BREAKEVEN = 0.524
ALL_TEST_YEARS = [2022, 2023, 2024, 2025]
N_BOOTSTRAP = 10000

CANDIDATES = {
    "Travel (all_games, pct=0.05)": ("travel", "all_games", 0.05),
    "Wind (favorite_home, pct=0.075)": ("wind", "favorite_home", 0.075),
}


def bucket_fn(df, dim):
    if dim == "travel":
        return df["home_travel_distance"].fillna(0) + df["away_travel_distance"].fillna(0)
    if dim == "wind":
        return df["wind_mph"]
    raise ValueError(dim)


def filter_fn(df, name):
    if name == "all_games":
        return pd.Series(True, index=df.index)
    if name == "favorite_home":
        return df["market_spread_open"] < 0
    raise ValueError(name)


def evaluate_year(full_df, test_year, dim, filter_name, pct):
    train_df = full_df[full_df["season"] == test_year - 1].copy()
    test_df = full_df[full_df["season"] == test_year].copy()

    train_df["bucket_val"] = bucket_fn(train_df, dim)
    test_df["bucket_val"] = bucket_fn(test_df, dim)
    train_df = train_df.dropna(subset=["bucket_val"])
    test_df = test_df.dropna(subset=["bucket_val"])

    train_df["decile"] = pd.qcut(train_df["bucket_val"], 10, labels=False, duplicates="drop")
    bins = pd.qcut(train_df["bucket_val"], 10, retbins=True, duplicates="drop")[1]
    bucket_avg = train_df.groupby("decile")["market_total_open"].mean()

    test_df["decile"] = pd.cut(test_df["bucket_val"], bins=bins, labels=False, include_lowest=True)
    test_df["expected_total"] = test_df["decile"].map(bucket_avg)
    test_df["deviation"] = test_df["market_total_open"] - test_df["expected_total"]
    test_df["actual_over"] = test_df["actual_total"] > test_df["market_total_open"]
    test_df = test_df[test_df["actual_total"] != test_df["market_total_open"]]
    test_df = test_df.dropna(subset=["deviation"])

    filtered = test_df[filter_fn(test_df, filter_name)]
    if len(filtered) < 20:
        return None

    low_cutoff = filtered["deviation"].quantile(pct)
    high_cutoff = filtered["deviation"].quantile(1 - pct)
    low_group = filtered[filtered["deviation"] <= low_cutoff]
    high_group = filtered[filtered["deviation"] >= high_cutoff]
    low_wins = int((low_group["actual_over"] == True).sum())
    high_wins = int((high_group["actual_over"] == False).sum())
    total = len(low_group) + len(high_group)
    wins = low_wins + high_wins
    return wins, total


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()].copy()

    for label, (dim, filter_name, pct) in CANDIDATES.items():
        print(f"\n{'='*70}\n{label}\n{'='*70}")

        all_correct = []
        pooled_wins = 0
        pooled_total = 0

        for test_year in ALL_TEST_YEARS:
            result = evaluate_year(full_df, test_year, dim, filter_name, pct)
            if result is None:
                print(f"  {test_year}: no bets")
                continue
            wins, total = result
            rate = wins / total * 100
            marker = " <-- above breakeven" if rate >= 52.4 else ""
            print(f"  {test_year}: {wins}/{total} = {rate:.1f}%{marker}")
            pooled_wins += wins
            pooled_total += total
            all_correct.extend([1] * wins + [0] * (total - wins))

        if pooled_total == 0:
            continue

        pooled_rate = pooled_wins / pooled_total * 100
        pvalue = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater").pvalue
        print(f"\n  POOLED: {pooled_wins}/{pooled_total} = {pooled_rate:.1f}% | p={pvalue:.4f}")

        all_correct = np.array(all_correct)
        rng = np.random.default_rng(42)
        bootstrap_rates = np.array([
            rng.choice(all_correct, size=len(all_correct), replace=True).mean() * 100
            for _ in range(N_BOOTSTRAP)
        ])
        pct_profitable = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
        print(f"  Bootstrap: {pct_profitable:.1f}% of resamples profitable")


if __name__ == "__main__":
    run()