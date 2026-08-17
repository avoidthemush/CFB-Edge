"""
Step 1 for the next checklist batch (travel, wind, def_ppa - all tied at
5 recurrences in the top 40): independent-split recheck on 2023 and
2024, using each dimension's best-looking percentile/filter combo from
the massive search as the starting point.
"""
import pandas as pd

CANDIDATES = {
    "travel (all_games, pct=0.05)": ("travel", "all_games", 0.05),
    "travel (favorite_home, pct=0.05)": ("travel", "favorite_home", 0.05),
    "wind (favorite_home, pct=0.075)": ("wind", "favorite_home", 0.075),
    "wind (low_wind, pct=0.05)": ("wind", "low_wind", 0.05),
    "def_ppa (early_season, pct=0.05)": ("def_ppa", "early_season", 0.05),
}

SPLITS = [2023, 2024]


def bucket_fn(df, dim):
    if dim == "travel":
        return df["home_travel_distance"].fillna(0) + df["away_travel_distance"].fillna(0)
    if dim == "wind":
        return df["wind_mph"]
    if dim == "def_ppa":
        return df["home_def_ppa"] + df["away_def_ppa"]
    raise ValueError(dim)


def filter_fn(df, name):
    if name == "all_games":
        return pd.Series(True, index=df.index)
    if name == "favorite_home":
        return df["market_spread_open"] < 0
    if name == "low_wind":
        return df["wind_mph"] < 10
    if name == "early_season":
        return df["week"] <= 4
    raise ValueError(name)


def evaluate(full_df, test_year, dim, filter_name, pct):
    train_df = full_df[full_df["season"] == test_year - 1].copy()
    test_df = full_df[full_df["season"] == test_year].copy()

    train_df["bucket_val"] = bucket_fn(train_df, dim)
    test_df["bucket_val"] = bucket_fn(test_df, dim)
    train_df = train_df.dropna(subset=["bucket_val"])
    test_df = test_df.dropna(subset=["bucket_val"])

    try:
        train_df["decile"] = pd.qcut(train_df["bucket_val"], 10, labels=False, duplicates="drop")
        bins = pd.qcut(train_df["bucket_val"], 10, retbins=True, duplicates="drop")[1]
    except ValueError:
        return None

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
    full_df = full_df[full_df["season"] <= 2024].copy()
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df["is_dome"] = full_df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})

    for label, (dim, filter_name, pct) in CANDIDATES.items():
        print(f"\n=== {label} ===")
        for test_year in SPLITS:
            result = evaluate(full_df, test_year, dim, filter_name, pct)
            if result is None:
                print(f"  {test_year}: insufficient data")
                continue
            wins, total = result
            rate = wins / total * 100
            marker = " <-- above breakeven" if rate >= 52.4 else ""
            print(f"  {test_year}: {wins}/{total} = {rate:.1f}%{marker}")


if __name__ == "__main__":
    run()