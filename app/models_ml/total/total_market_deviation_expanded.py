"""
Expanded Market Deviation search - genuinely broader than the first
pass, not just padding: 8 bucket dimensions (up from 4), 6 percentile
thresholds (up from 4), 14 situational filters (up from 7), PLUS
two-dimensional bucketing (pairs of factors combined into a joint grid)
- a mathematically distinct question from single-factor bucketing: is
the market mispricing the INTERSECTION of two conditions, not just one.

Deliberately allowed to run long (many combinations, real compute).
Phase 1 discipline: 3 safe years only, 2025 held back.
"""
import itertools
import pandas as pd
import numpy as np

SAFE_TEST_YEARS = [2022, 2023, 2024]
PERCENTILES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
MIN_BETS_REQUIRED = 100

BUCKET_DIMENSIONS = {
    "pace": lambda df: df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"],
    "third_down": lambda df: df["home_off_third_down_pct"] + df["away_off_third_down_pct"],
    "off_efficiency": lambda df: df["home_off_success_rate"] + df["away_off_success_rate"],
    "wind": lambda df: df["wind_mph"],
    "def_ppa": lambda df: df["home_def_ppa"] + df["away_def_ppa"],
    "off_explosiveness": lambda df: df["home_off_explosiveness"] + df["away_off_explosiveness"],
    "turnover_gap": lambda df: (df["home_turnover_margin"] - df["away_turnover_margin"]).abs(),
    "field_position": lambda df: df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"],
}

SITUATIONAL_FILTERS = {
    "all_games": lambda df: pd.Series(True, index=df.index),
    "weeks_1_4": lambda df: df["week"] <= 4,
    "weeks_5_9": lambda df: (df["week"] >= 5) & (df["week"] <= 9),
    "weeks_10_plus": lambda df: df["week"] >= 10,
    "outdoor_only": lambda df: df["is_dome"] != True,
    "dome_only": lambda df: df["is_dome"] == True,
    "conference_games": lambda df: df["is_conference_game"] == 1,
    "non_conference_games": lambda df: df["is_conference_game"] == 0,
    "high_wind": lambda df: df["wind_mph"] >= 10,
    "low_wind": lambda df: df["wind_mph"] < 10,
    "early_season": lambda df: df["week"] <= 6,
    "late_season": lambda df: df["week"] > 6,
    "neutral_site": lambda df: df["neutral_site"] == True,
    "non_neutral": lambda df: df["neutral_site"] != True,
}


def compute_single_deviation(full_df, test_year, bucket_fn):
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


def compute_pair_deviation(full_df, test_year, bucket_fn_1, bucket_fn_2):
    train_df = full_df[full_df["season"] == test_year - 1].copy()
    test_df = full_df[full_df["season"] == test_year].copy()

    train_df["b1"] = bucket_fn_1(train_df)
    train_df["b2"] = bucket_fn_2(train_df)
    test_df["b1"] = bucket_fn_1(test_df)
    test_df["b2"] = bucket_fn_2(test_df)
    train_df = train_df.dropna(subset=["b1", "b2"])
    test_df = test_df.dropna(subset=["b1", "b2"])
    if len(train_df) < 100:
        return None

    # 5x5 joint grid (coarser than 1D's 10 buckets - fewer games per cell)
    try:
        train_df["d1"] = pd.qcut(train_df["b1"], 5, labels=False, duplicates="drop")
        train_df["d2"] = pd.qcut(train_df["b2"], 5, labels=False, duplicates="drop")
    except ValueError:
        return None

    bucket_avg = train_df.groupby(["d1", "d2"])["market_total_open"].mean()

    bins1 = pd.qcut(train_df["b1"], 5, retbins=True, duplicates="drop")[1]
    bins2 = pd.qcut(train_df["b2"], 5, retbins=True, duplicates="drop")[1]
    test_df["d1"] = pd.cut(test_df["b1"], bins=bins1, labels=False, include_lowest=True)
    test_df["d2"] = pd.cut(test_df["b2"], bins=bins2, labels=False, include_lowest=True)

    test_df["expected_total"] = test_df.apply(
        lambda row: bucket_avg.get((row["d1"], row["d2"]), np.nan), axis=1
    )
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

    print("=== PART 1: Single-dimension bucketing (8 dims x 6 percentiles x 14 filters) ===")
    for bucket_name, bucket_fn in BUCKET_DIMENSIONS.items():
        deviation_by_year = {}
        for test_year in SAFE_TEST_YEARS:
            dev_df = compute_single_deviation(full_df, test_year, bucket_fn)
            if dev_df is not None:
                deviation_by_year[test_year] = dev_df

        for percentile in PERCENTILES:
            for filter_name, filter_fn in SITUATIONAL_FILTERS.items():
                pooled_wins, pooled_total, years_cleared, years_checked = 0, 0, 0, 0
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
                results.append((f"1D:{bucket_name}", percentile, filter_name, pooled_rate, pooled_total, years_cleared, years_checked))

    print(f"  Done - {len(results)} combos so far\n")

    print("=== PART 2: Two-dimensional bucketing (pairs of factors, joint grid) ===")
    dim_names = list(BUCKET_DIMENSIONS.keys())
    pair_count = 0
    for dim1, dim2 in itertools.combinations(dim_names, 2):
        pair_count += 1
        deviation_by_year = {}
        for test_year in SAFE_TEST_YEARS:
            dev_df = compute_pair_deviation(full_df, test_year, BUCKET_DIMENSIONS[dim1], BUCKET_DIMENSIONS[dim2])
            if dev_df is not None:
                deviation_by_year[test_year] = dev_df

        for percentile in [0.15, 0.20, 0.25]:  # fewer percentiles for pairs, given more combos already
            for filter_name in ["all_games", "outdoor_only", "weeks_5_9"]:  # fewer filters for pairs
                filter_fn = SITUATIONAL_FILTERS[filter_name]
                pooled_wins, pooled_total, years_cleared, years_checked = 0, 0, 0, 0
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
                results.append((f"2D:{dim1}+{dim2}", percentile, filter_name, pooled_rate, pooled_total, years_cleared, years_checked))

    print(f"  Done - {pair_count} dimension pairs tested\n")

    results.sort(key=lambda x: -x[3])
    print(f"\nTOTAL combinations found with >={MIN_BETS_REQUIRED} bets: {len(results)}\n")
    print("=== TOP 20 ===")
    for bucket, pct, filt, rate, n, cleared, checked in results[:20]:
        marker = " <-- above breakeven" if rate >= 52.4 else ""
        print(f"  {rate:.1f}% ({n} bets, {cleared}/{checked} years cleared): "
              f"bucket={bucket}, pct={pct}, filter={filt}{marker}")


if __name__ == "__main__":
    run()