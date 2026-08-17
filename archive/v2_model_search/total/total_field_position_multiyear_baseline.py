"""
Tests whether Field Position Deviation is more robust when the
"expected total per bucket" baseline is built from MULTIPLE prior
years instead of just one - directly addresses a real fragility
concern: a single prior season gives a thin, more easily-skewed
baseline (~78 games per bucket). If a multi-year baseline performs
similarly or better, that's real evidence this isn't a fragile,
single-season fluke.
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest

PCT = 0.075
BREAKEVEN = 0.524
ALL_TEST_YEARS = [2023, 2024, 2025]  # need 2+ prior years, so start at 2023
N_BOOTSTRAP = 10000


def bucket_fn(df):
    return df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()].copy()

    for baseline_years_back in [1, 2, 3]:
        print(f"\n{'='*70}")
        print(f"Baseline built from {baseline_years_back} prior year(s)")
        print(f"{'='*70}")

        all_correct = []
        pooled_wins = 0
        pooled_total = 0

        for test_year in ALL_TEST_YEARS:
            train_start = test_year - baseline_years_back
            train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] < test_year)].copy()
            test_df = full_df[full_df["season"] == test_year].copy()

            if len(train_df) < 200:
                print(f"  {test_year}: insufficient training data ({len(train_df)} games)")
                continue

            train_df["bucket_val"] = bucket_fn(train_df)
            test_df["bucket_val"] = bucket_fn(test_df)
            train_df = train_df.dropna(subset=["bucket_val"])
            test_df = test_df.dropna(subset=["bucket_val"])

            train_df["decile"] = pd.qcut(train_df["bucket_val"], 10, labels=False, duplicates="drop")
            bucket_avg = train_df.groupby("decile")["market_total_open"].mean()
            bucket_counts = train_df.groupby("decile").size()

            bins = pd.qcut(train_df["bucket_val"], 10, retbins=True, duplicates="drop")[1]
            test_df["decile"] = pd.cut(test_df["bucket_val"], bins=bins, labels=False, include_lowest=True)
            test_df["expected_total"] = test_df["decile"].map(bucket_avg)
            test_df["deviation"] = test_df["market_total_open"] - test_df["expected_total"]
            test_df["actual_over"] = test_df["actual_total"] > test_df["market_total_open"]
            test_df = test_df[test_df["actual_total"] != test_df["market_total_open"]]
            test_df = test_df.dropna(subset=["deviation"])

            low_cutoff = test_df["deviation"].quantile(PCT)
            high_cutoff = test_df["deviation"].quantile(1 - PCT)
            low_group = test_df[test_df["deviation"] <= low_cutoff]
            high_group = test_df[test_df["deviation"] >= high_cutoff]

            low_wins = int((low_group["actual_over"] == True).sum())
            high_wins = int((high_group["actual_over"] == False).sum())
            combined_wins = low_wins + high_wins
            combined_total = len(low_group) + len(high_group)
            combined_rate = combined_wins / combined_total * 100 if combined_total > 0 else 0

            avg_bucket_size = bucket_counts.mean()
            marker = " <-- above breakeven" if combined_rate >= 52.4 else ""
            print(f"  {test_year}: {combined_wins}/{combined_total} = {combined_rate:.1f}%{marker} "
                  f"(avg {avg_bucket_size:.0f} games/bucket in baseline)")

            pooled_wins += combined_wins
            pooled_total += combined_total
            low_correct = [1] * low_wins + [0] * (len(low_group) - low_wins)
            high_correct = [1] * high_wins + [0] * (len(high_group) - high_wins)
            all_correct.extend(low_correct + high_correct)

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