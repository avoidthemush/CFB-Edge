"""
Type B (market anomaly) test for Spread, mirroring Total's successful
Market Deviation approach: bucket prior-year games by talent gap
(diff_sp+_rating), find the market's typical spread for each bucket,
then bet when THIS game's posted spread deviates unusually from that
baseline - not predicting the outcome, just detecting when the market's
own number looks inconsistent with how it usually prices similar gaps.

Phase 1 discipline: tests 3 safe years first (2022-2024), 2025 held back
until this earns it.
"""
import pandas as pd

PERCENTILE = 0.15
SAFE_TEST_YEARS = [2022, 2023, 2024]


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024].copy()
    full_df = full_df[full_df["market_spread_open"].notna() & full_df["actual_spread"].notna()]
    full_df = full_df.dropna(subset=["diff_sp+_rating"])

    for test_year in SAFE_TEST_YEARS:
        train_df = full_df[full_df["season"] == test_year - 1].copy()
        test_df = full_df[full_df["season"] == test_year].copy()

        # Bucket prior year's games by talent-gap decile, find each
        # bucket's typical market spread
        train_df["gap_decile"] = pd.qcut(train_df["diff_sp+_rating"].abs(), 10, labels=False, duplicates="drop")
        bucket_avg_spread = train_df.groupby("gap_decile")["market_spread_open"].apply(lambda x: x.abs().mean())

        bins = pd.qcut(train_df["diff_sp+_rating"].abs(), 10, retbins=True, duplicates="drop")[1]
        test_df["gap_decile"] = pd.cut(test_df["diff_sp+_rating"].abs(), bins=bins, labels=False, include_lowest=True)
        test_df["expected_spread_magnitude"] = test_df["gap_decile"].map(bucket_avg_spread)
        test_df["actual_spread_magnitude"] = test_df["market_spread_open"].abs()
        test_df["spread_deviation"] = test_df["actual_spread_magnitude"] - test_df["expected_spread_magnitude"]
        test_df = test_df.dropna(subset=["spread_deviation"])

        # Theory: market spread unusually SMALL for this talent gap ->
        # the favorite is being underpriced -> bet the FAVORITE to cover
        # market spread unusually LARGE for this talent gap -> the
        # underdog is being overpriced -> bet the UNDERDOG to cover
        test_df["open_implied_margin"] = -test_df["market_spread_open"]
        test_df["home_covered"] = test_df["actual_spread"] > test_df["open_implied_margin"]
        test_df = test_df[test_df["actual_spread"] != test_df["open_implied_margin"]]

        test_df["home_is_favorite"] = test_df["market_spread_open"] < 0

        low_cutoff = test_df["spread_deviation"].quantile(PERCENTILE)
        high_cutoff = test_df["spread_deviation"].quantile(1 - PERCENTILE)

        # Small-deviation group: bet the FAVORITE (whichever team that is)
        small_group = test_df[test_df["spread_deviation"] <= low_cutoff]
        small_favorite_covers = (
            (small_group["home_is_favorite"] & small_group["home_covered"]) |
            (~small_group["home_is_favorite"] & ~small_group["home_covered"])
        )
        small_wins = int(small_favorite_covers.sum())

        # Large-deviation group: bet the UNDERDOG
        large_group = test_df[test_df["spread_deviation"] >= high_cutoff]
        large_underdog_covers = (
            (large_group["home_is_favorite"] & ~large_group["home_covered"]) |
            (~large_group["home_is_favorite"] & large_group["home_covered"])
        )
        large_wins = int(large_underdog_covers.sum())

        combined_wins = small_wins + large_wins
        combined_total = len(small_group) + len(large_group)
        combined_rate = combined_wins / combined_total * 100 if combined_total > 0 else 0

        marker = " <-- above breakeven" if combined_rate >= 52.4 else ""
        print(f"{test_year}: small-deviation (bet favorite) n={len(small_group)} ({small_wins} wins), "
              f"large-deviation (bet underdog) n={len(large_group)} ({large_wins} wins)")
        print(f"  Combined: {combined_wins}/{combined_total} = {combined_rate:.1f}%{marker}\n")


if __name__ == "__main__":
    run()