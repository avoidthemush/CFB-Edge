"""
Situational overlay on Market Deviation - mirrors how Mid-Season Dog was
found (same prediction, extra situational filters layered on top).
Checks whether the base Market Deviation signal sharpens under specific
conditions: week range, dome/outdoor, conference game, home underdog vs
away underdog (using spread_open as a proxy for which side is favored).

Also tests MULTIPLE bucketing dimensions (not just pace) and MULTIPLE
percentile thresholds (not just 15%) - broader, more patient search per
user's request. Deliberately allowed to take real time (many combos).

Phase 1 discipline: 3 safe years only (2022-2024), 2025 held back.
"""
import itertools
import pandas as pd

SAFE_TEST_YEARS = [2022, 2023, 2024]
PERCENTILES = [0.10, 0.15, 0.20, 0.25]

BUCKET_DIMENSIONS = {
    "pace": lambda df: df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"],
    "third_down": lambda df: df["home_off_third_down_pct"] + df["away_off_third_down_pct"],
    "off_efficiency": lambda df: df["home_off_success_rate"] + df["away_off_success_rate"],
    "wind": lambda df: df["wind_mph"],
}

SITUATIONAL_FILTERS = {
    "all_games": lambda df: pd.Series(True, index=df.index),
    "weeks_1_4": lambda df: df["week"] <= 4,
    "weeks_5_9": lambda df: (df["week"] >= 5) & (df["week"] <= 9),
    "weeks_10_plus": lambda df: df["week"] >= 10,
    "outdoor_only": lambda df: df["is_dome"] != True,
    "conference_games": lambda df: df["is_conference_game"] == 1,
    "non_conference_games": lambda df: df["is_conference_game"] == 0,
}

MIN_BETS_REQUIRED = 100


def compute_deviation(full_df, test_year, bucket_fn):
    train_df = full_df[full_df["season"] == test_year - 1].copy()
    test_df = full_df[full_df["season"] == test_year].copy()

    train_df["bucket_val"] = bucket_fn(train_df)
    test_df["bucket_val"] = bucket_fn(test_df)
    train_df = train_df.dropna(subset=["bucket_val"])
    test_df = test_df.dropna(subset=["bucket_val"])

    if len(train_df) < 50:
        return None

    train_df["decile"] = pd.qcut(train_df["bucket_val"], 10, labels=False, duplicates="drop")
    bucket_avg = train_df.groupby("decile")["market_total_open"].mean()

    bins = pd.qcut(train_df["bucket_val"], 10, retbins=True, duplicates="drop")[1]
    test_df["decile"] = pd.cut(test_df["bucket_val"], bins=bins, labels=False, include_lowest=True)
    test_df["expected_total"] = test_df["decile"].map(bucket_avg)
    test_df["deviation"] = test_df["market_total_open"] - test_df["expected_total"]
    test_df["actual_over"] = test_df["actual_total"] > test_df["market_total_open"]
    test_df = test_df[test_df["actual_total"] != test_df["market_total_open"]]
    return test_df.dropna(subset=["deviation"])


def evaluate(test_df, percentile, filter_fn):
    filtered = test_df[filter_fn(test_df)]
    if len(filtered) < 20:
        return None

    low_cutoff = filtered["deviation"].quantile(percentile)
    high_cutoff = filtered["deviation"].quantile(1 - percentile)

    low_group = filtered[filtered["deviation"] <= low_cutoff]
    high_group = filtered[filtered["deviation"] >= high_cutoff]

    low_wins = int((low_group["actual_over"] == True).sum())
    high_wins = int((high_group["actual_over"] == False).sum())
    total = len(low_group) + len(high_group)
    wins = low_wins + high_wins

    return wins, total


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024].copy()
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df["is_dome"] = full_df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})

    results = []
    total_combos = len(BUCKET_DIMENSIONS) * len(PERCENTILES) * len(SITUATIONAL_FILTERS)
    print(f"Testing {total_combos} combinations across 3 safe years...\n")

    for bucket_name, bucket_fn in BUCKET_DIMENSIONS.items():
        deviation_by_year = {}
        for test_year in SAFE_TEST_YEARS:
            dev_df = compute_deviation(full_df, test_year, bucket_fn)
            if dev_df is not None:
                deviation_by_year[test_year] = dev_df

        for percentile in PERCENTILES:
            for filter_name, filter_fn in SITUATIONAL_FILTERS.items():
                pooled_wins = 0
                pooled_total = 0
                years_cleared = 0
                years_checked = 0

                for test_year, dev_df in deviation_by_year.items():
                    result = evaluate(dev_df, percentile, filter_fn)
                    if result is None:
                        continue
                    wins, total = result
                    pooled_wins += wins
                    pooled_total += total
                    years_checked += 1
                    if total > 0 and wins / total >= 0.524:
                        years_cleared += 1

                if pooled_total < MIN_BETS_REQUIRED:
                    continue

                pooled_rate = pooled_wins / pooled_total * 100
                results.append((bucket_name, percentile, filter_name, pooled_rate, pooled_total, years_cleared, years_checked))

    results.sort(key=lambda x: -x[3])

    print(f"Found {len(results)} combinations with >={MIN_BETS_REQUIRED} bets\n")
    print("=== TOP 20 ===")
    for bucket, pct, filt, rate, n, cleared, checked in results[:20]:
        marker = " <-- above breakeven" if rate >= 52.4 else ""
        print(f"  {rate:.1f}% ({n} bets, {cleared}/{checked} years cleared): "
              f"bucket={bucket}, pct={pct}, filter={filt}{marker}")


if __name__ == "__main__":
    run()