"""
Different kind of signal: instead of predicting the total ourselves,
checks whether the MARKET's own posted total looks like an outlier
relative to recent games with similar combined pace - a market-
mispricing detector, not a scoring predictor. Tests on 3 safe years only.
"""
import numpy as np
import pandas as pd

GAP_PERCENTILE_THRESHOLDS = [0.10, 0.15, 0.20]  # bet when market total is in bottom/top X% for similar-pace games
SAFE_TEST_YEARS = [2022, 2023, 2024]


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024].copy()
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df["combined_pace"] = full_df["home_off_plays_per_drive"] + full_df["away_off_plays_per_drive"]
    full_df = full_df.dropna(subset=["combined_pace"])

    all_bets = []

    for test_year in SAFE_TEST_YEARS:
        train_df = full_df[full_df["season"] == test_year - 1]  # prior year only, as the "recent comparable games" pool
        test_df = full_df[full_df["season"] == test_year].copy()

        # Bucket prior year's games by pace decile, get each bucket's
        # average market_total_open as the "expected" market level
        train_df = train_df.copy()
        train_df["pace_decile"] = pd.qcut(train_df["combined_pace"], 10, labels=False, duplicates="drop")
        bucket_avg_total = train_df.groupby("pace_decile")["market_total_open"].mean()

        test_df["pace_decile"] = pd.cut(
            test_df["combined_pace"],
            bins=pd.qcut(train_df["combined_pace"], 10, retbins=True, duplicates="drop")[1],
            labels=False, include_lowest=True,
        )
        test_df["expected_market_total"] = test_df["pace_decile"].map(bucket_avg_total)
        test_df["market_deviation"] = test_df["market_total_open"] - test_df["expected_market_total"]
        test_df["actual_over"] = test_df["actual_total"] > test_df["market_total_open"]
        test_df = test_df[test_df["actual_total"] != test_df["market_total_open"]]
        test_df = test_df.dropna(subset=["market_deviation"])

        all_bets.append(test_df[["market_deviation", "actual_over"]])

    bets = pd.concat(all_bets, ignore_index=True)
    print(f"Total games with valid deviation score: {len(bets)}\n")

    for pct in GAP_PERCENTILE_THRESHOLDS:
        low_cutoff = bets["market_deviation"].quantile(pct)
        high_cutoff = bets["market_deviation"].quantile(1 - pct)

        # Theory: market total unusually LOW for this pace level -> bet OVER
        # market total unusually HIGH for this pace level -> bet UNDER
        low_group = bets[bets["market_deviation"] <= low_cutoff]
        high_group = bets[bets["market_deviation"] >= high_cutoff]

        low_wins = (low_group["actual_over"] == True).mean() * 100 if len(low_group) > 0 else 0
        high_wins = (high_group["actual_over"] == False).mean() * 100 if len(high_group) > 0 else 0

        combined_wins = (
            (low_group["actual_over"] == True).sum() + (high_group["actual_over"] == False).sum()
        )
        combined_total = len(low_group) + len(high_group)
        combined_rate = combined_wins / combined_total * 100 if combined_total > 0 else 0

        print(f"Percentile {pct}: low group n={len(low_group)} (bet OVER, {low_wins:.1f}% win), "
              f"high group n={len(high_group)} (bet UNDER, {high_wins:.1f}% win)")
        marker = " <-- above breakeven" if combined_rate >= 52.4 else ""
        print(f"  Combined: {combined_total} bets, {combined_rate:.1f}%{marker}\n")


if __name__ == "__main__":
    run()