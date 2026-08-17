"""
Tests favorite_home as a TAG on the already-approved Pace Deviation
system (mirrors how Mid-Season Dog relates to General Model) - not a
new independent system. Full test including 2025, since this earned it
via independence check + strong, credible-sample-size recheck.
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest

BREAKEVEN = 0.524
ALL_TEST_YEARS = [2022, 2023, 2024, 2025]
N_BOOTSTRAP = 10000
PCT = 0.15


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()].copy()

    all_correct = []
    pooled_wins = 0
    pooled_total = 0

    for test_year in ALL_TEST_YEARS:
        train_df = full_df[full_df["season"] == test_year - 1].copy()
        test_df = full_df[full_df["season"] == test_year].copy()

        train_df["bucket_val"] = train_df["home_off_plays_per_drive"] + train_df["away_off_plays_per_drive"]
        test_df["bucket_val"] = test_df["home_off_plays_per_drive"] + test_df["away_off_plays_per_drive"]
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

        # TAG: restrict to home-favorite games only
        filtered = test_df[test_df["market_spread_open"] < 0]

        low_cutoff = filtered["deviation"].quantile(PCT)
        high_cutoff = filtered["deviation"].quantile(1 - PCT)
        low_group = filtered[filtered["deviation"] <= low_cutoff]
        high_group = filtered[filtered["deviation"] >= high_cutoff]

        low_wins = int((low_group["actual_over"] == True).sum())
        high_wins = int((high_group["actual_over"] == False).sum())
        combined_wins = low_wins + high_wins
        combined_total = len(low_group) + len(high_group)
        combined_rate = combined_wins / combined_total * 100 if combined_total > 0 else 0

        marker = " <-- above breakeven" if combined_rate >= 52.4 else ""
        print(f"{test_year}: {combined_wins}/{combined_total} = {combined_rate:.1f}%{marker}")

        pooled_wins += combined_wins
        pooled_total += combined_total
        low_correct = [1] * low_wins + [0] * (len(low_group) - low_wins)
        high_correct = [1] * high_wins + [0] * (len(high_group) - high_wins)
        all_correct.extend(low_correct + high_correct)

    pooled_rate = pooled_wins / pooled_total * 100
    pvalue = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater").pvalue
    print(f"\nPOOLED: {pooled_wins}/{pooled_total} = {pooled_rate:.1f}% | p={pvalue:.4f}")

    all_correct = np.array(all_correct)
    rng = np.random.default_rng(42)
    bootstrap_rates = np.array([
        rng.choice(all_correct, size=len(all_correct), replace=True).mean() * 100
        for _ in range(N_BOOTSTRAP)
    ])
    pct_profitable = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
    print(f"Bootstrap: {pct_profitable:.1f}% of resamples profitable")


if __name__ == "__main__":
    run()