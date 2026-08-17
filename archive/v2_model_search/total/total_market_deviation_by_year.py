"""
Year-by-year breakdown of the market-deviation approach - the pooled
result looked strong, but every prior Total approach has struggled
specifically on 2022. Checking whether this one is genuinely different
(works in all 3 safe years) before deciding whether it's earned a real
look at 2025.
"""
import pandas as pd

PERCENTILE = 0.15  # middle-ground threshold from the pooled test
SAFE_TEST_YEARS = [2022, 2023, 2024]


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024].copy()
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df["combined_pace"] = full_df["home_off_plays_per_drive"] + full_df["away_off_plays_per_drive"]
    full_df = full_df.dropna(subset=["combined_pace"])

    for test_year in SAFE_TEST_YEARS:
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
        print(f"Test {test_year}: low group n={len(low_group)} ({low_wins} wins, "
              f"{low_wins/len(low_group)*100:.1f}%), high group n={len(high_group)} "
              f"({high_wins} wins, {high_wins/len(high_group)*100:.1f}%)")
        print(f"  Combined: {combined_wins}/{combined_total} = {combined_rate:.1f}%{marker}\n")


if __name__ == "__main__":
    run()