"""
Phase 2 confirmation for the Market Deviation approach - the first Total
candidate to clear all three safe years. Full test including 2025 (a
real, deliberate spend, earned by clearing 2022/2023/2024 first) with
proper significance testing and bootstrap.
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest

PERCENTILE = 0.15
ALL_TEST_YEARS = [2022, 2023, 2024, 2025]
BREAKEVEN = 0.524
N_BOOTSTRAP = 10000


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()].copy()
    full_df["combined_pace"] = full_df["home_off_plays_per_drive"] + full_df["away_off_plays_per_drive"]
    full_df = full_df.dropna(subset=["combined_pace"])

    all_correct = []
    pooled_wins = 0
    pooled_total = 0

    for test_year in ALL_TEST_YEARS:
        train_df = full_df[full_df["season"] == test_year - 1].copy()
        test_df = full_df[full_df["season"] == test_year].copy()

        train_df["pace_decile"] = pd.qcut(train_df["combined_pace"], 10, labels=False, duplicates="drop")
        bucket_avg_total = train_df.groupby("pace_decile")["market_total_open"].mean()

        bins = pd.qcut(train_df["combined_pace"], 10, retbins=True, duplicates="drop")[1]
        test_df["pace_decile"] = pd.cut(test_df["combined_pace"], bins=bins, labels=False, include_lowest=True)
        test_df["expected_market_total"] = test_df["pace_decile"].map(bucket_avg_total)
        test_df["market_deviation"] = test_df["market_total_open"] - test_df["expected_market_total"]
        test_df["actual_over"] = test_df["actual_total"] > test_df["market_total_open"]
        test_df = test_df[test_df["actual_total"] != test_df["market_total_open"]]
        test_df = test_df.dropna(subset=["market_deviation"])

        low_cutoff = test_df["market_deviation"].quantile(PERCENTILE)
        high_cutoff = test_df["market_deviation"].quantile(1 - PERCENTILE)

        low_group = test_df[test_df["market_deviation"] <= low_cutoff]
        high_group = test_df[test_df["market_deviation"] >= high_cutoff]

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
    ci_low, ci_high = np.percentile(bootstrap_rates, [2.5, 97.5])
    print(f"Bootstrap: {pct_profitable:.1f}% of resamples profitable, 95% CI [{ci_low:.1f}%, {ci_high:.1f}%]")


if __name__ == "__main__":
    run()