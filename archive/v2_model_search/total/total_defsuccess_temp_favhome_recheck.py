"""
Next checklist batch: def_success_allowed, temp (3 recurrences each),
plus favorite_home tested as a standalone filter question (7
recurrences in the top 40, tied for most of any filter, never tested on
its own). Independent-split recheck first (2023, 2024).
"""
import pandas as pd

CANDIDATES = {
    "def_success_allowed (early_season, pct=0.05)": ("def_success_allowed", "early_season", 0.05),
    "def_success_allowed (low_wind, pct=0.05)": ("def_success_allowed", "low_wind", 0.05),
    "temp (high_total_open, pct=0.05)": ("temp", "high_total_open", 0.05),
    "favorite_home standalone (pace bucket, all favorite-home games)": ("pace", "favorite_home", 0.15),
}

SPLITS = [2023, 2024]


def bucket_fn(df, dim):
    if dim == "def_success_allowed":
        return df["home_def_success_rate_allowed"] + df["away_def_success_rate_allowed"]
    if dim == "temp":
        return df["temp_f"]
    if dim == "pace":
        return df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
    raise ValueError(dim)


def filter_fn(df, name):
    if name == "early_season":
        return df["week"] <= 4
    if name == "low_wind":
        return df["wind_mph"] < 10
    if name == "high_total_open":
        return df["market_total_open"] >= 55
    if name == "favorite_home":
        return df["market_spread_open"] < 0
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