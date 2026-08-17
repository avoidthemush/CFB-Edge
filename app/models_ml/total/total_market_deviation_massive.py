"""
Large-scale Market Deviation search - ~10,000 combinations across
single/pair/triple-dimension bucketing, multiple percentile thresholds,
and multiple situational filters. Genuinely more compute than prior
passes, deliberately allowed to take real wall-clock time.

Triple-dimension bucketing is a real, new question: is the market
mispricing the INTERSECTION of three conditions at once (e.g. fast pace
+ high third-down rate + low wind), not just one or two factors in
isolation. Uses coarser bins (3 per dimension) since sample size shrinks
fast with more dimensions - flagged as a real limitation, not hidden.

Phase 1 discipline: 3 safe years only (2022-2024), 2025 held back.
"""
import itertools
import numpy as np
import pandas as pd

SAFE_TEST_YEARS = [2022, 2023, 2024]
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
    "def_success_allowed": lambda df: df["home_def_success_rate_allowed"] + df["away_def_success_rate_allowed"],
    "off_points_per_opp": lambda df: df["home_off_points_per_opportunity"] + df["away_off_points_per_opportunity"],
    "travel": lambda df: df["home_travel_distance"].fillna(0) + df["away_travel_distance"].fillna(0),
    "temp": lambda df: df["temp_f"],
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
    "favorite_home": lambda df: df["market_spread_open"] < 0,
    "favorite_away": lambda df: df["market_spread_open"] > 0,
    "big_spread": lambda df: df["market_spread_open"].abs() >= 14,
    "small_spread": lambda df: df["market_spread_open"].abs() < 7,
    "high_total_open": lambda df: df["market_total_open"] >= 55,
    "low_total_open": lambda df: df["market_total_open"] < 55,
}

SINGLE_PERCENTILES = [0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.225, 0.25, 0.275]
PAIR_PERCENTILES = [0.10, 0.15, 0.20, 0.25, 0.275, 0.30]
TRIPLE_PERCENTILES = [0.15, 0.20, 0.25, 0.30]

PAIR_FILTERS = ["all_games", "outdoor_only", "weeks_5_9", "weeks_1_4", "weeks_10_plus",
                "conference_games", "non_conference_games", "low_wind"]
TRIPLE_FILTERS = ["all_games", "outdoor_only", "weeks_5_9", "non_conference_games", "low_wind"]


def compute_deviation(full_df, test_year, bucket_fns, n_bins):
    train_df = full_df[full_df["season"] == test_year - 1].copy()
    test_df = full_df[full_df["season"] == test_year].copy()

    bucket_cols = []
    for i, fn in enumerate(bucket_fns):
        col = f"b{i}"
        train_df[col] = fn(train_df)
        test_df[col] = fn(test_df)
        bucket_cols.append(col)

    train_df = train_df.dropna(subset=bucket_cols)
    test_df = test_df.dropna(subset=bucket_cols)
    if len(train_df) < 50:
        return None

    decile_cols = []
    for col in bucket_cols:
        try:
            train_df[col + "_d"], bins = pd.qcut(train_df[col], n_bins, labels=False, duplicates="drop", retbins=True)
        except ValueError:
            return None
        test_df[col + "_d"] = pd.cut(test_df[col], bins=bins, labels=False, include_lowest=True)
        decile_cols.append(col + "_d")

    test_df = test_df.dropna(subset=decile_cols)
    if len(test_df) == 0:
        return None

    bucket_avg = train_df.groupby(decile_cols)["market_total_open"].mean()

    if len(decile_cols) == 1:
        test_df["expected_total"] = test_df[decile_cols[0]].map(bucket_avg)
    else:
        keys = list(zip(*[test_df[c] for c in decile_cols]))
        test_df["expected_total"] = [bucket_avg.get(k, np.nan) for k in keys]

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


def score_combo(full_df, bucket_fns, n_bins, percentile, filter_name):
    filter_fn = SITUATIONAL_FILTERS[filter_name]
    pooled_wins, pooled_total, years_cleared, years_checked = 0, 0, 0, 0
    for test_year in SAFE_TEST_YEARS:
        dev_df = compute_deviation(full_df, test_year, bucket_fns, n_bins)
        if dev_df is None:
            continue
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
        return None
    return pooled_wins / pooled_total * 100, pooled_total, years_cleared, years_checked


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024].copy()
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df["is_dome"] = full_df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})

    results = []
    dim_names = list(BUCKET_DIMENSIONS.keys())

    print(f"=== PART 1: Single dimensions ({len(dim_names)} dims x {len(SINGLE_PERCENTILES)} "
          f"pct x {len(SITUATIONAL_FILTERS)} filters) ===")
    count = 0
    for dim in dim_names:
        for pct in SINGLE_PERCENTILES:
            for filt in SITUATIONAL_FILTERS:
                count += 1
                r = score_combo(full_df, [BUCKET_DIMENSIONS[dim]], 10, pct, filt)
                if r:
                    results.append((f"1D:{dim}", pct, filt, *r))
    print(f"  Tested {count} combos, {len([r for r in results if r[0].startswith('1D')])} valid\n")

    print(f"=== PART 2: Pairs (C({len(dim_names)},2)={len(list(itertools.combinations(dim_names,2)))} "
          f"pairs x {len(PAIR_PERCENTILES)} pct x {len(PAIR_FILTERS)} filters) ===")
    count = 0
    for dim1, dim2 in itertools.combinations(dim_names, 2):
        for pct in PAIR_PERCENTILES:
            for filt in PAIR_FILTERS:
                count += 1
                r = score_combo(full_df, [BUCKET_DIMENSIONS[dim1], BUCKET_DIMENSIONS[dim2]], 5, pct, filt)
                if r:
                    results.append((f"2D:{dim1}+{dim2}", pct, filt, *r))
    print(f"  Tested {count} combos\n")

    print(f"=== PART 3: Triples (C({len(dim_names)},3)={len(list(itertools.combinations(dim_names,3)))} "
          f"triples x {len(TRIPLE_PERCENTILES)} pct x {len(TRIPLE_FILTERS)} filters) ===")
    count = 0
    for dim1, dim2, dim3 in itertools.combinations(dim_names, 3):
        for pct in TRIPLE_PERCENTILES:
            for filt in TRIPLE_FILTERS:
                count += 1
                r = score_combo(full_df, [BUCKET_DIMENSIONS[dim1], BUCKET_DIMENSIONS[dim2], BUCKET_DIMENSIONS[dim3]], 3, pct, filt)
                if r:
                    results.append((f"3D:{dim1}+{dim2}+{dim3}", pct, filt, *r))
    print(f"  Tested {count} combos\n")

    total_tested = (len(dim_names) * len(SINGLE_PERCENTILES) * len(SITUATIONAL_FILTERS) +
                     len(list(itertools.combinations(dim_names, 2))) * len(PAIR_PERCENTILES) * len(PAIR_FILTERS) +
                     len(list(itertools.combinations(dim_names, 3))) * len(TRIPLE_PERCENTILES) * len(TRIPLE_FILTERS))
    print(f"TOTAL combinations tested: {total_tested}")
    print(f"TOTAL valid (>={MIN_BETS_REQUIRED} bets): {len(results)}\n")

    results.sort(key=lambda x: -x[3])
    print("=== TOP 40 ===")
    for bucket, pct, filt, rate, n, cleared, checked in results[:40]:
        marker = " <-- above breakeven" if rate >= 52.4 else ""
        print(f"  {rate:.1f}% ({n} bets, {cleared}/{checked} years cleared): "
              f"bucket={bucket}, pct={pct}, filter={filt}{marker}")


if __name__ == "__main__":
    run()