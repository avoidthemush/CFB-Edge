"""
Second-split confirmation for field_position - the dominant recurring
dimension across the top 40 results (12 of 40, nearly 3x the next-best
single dimension). Testing the cleanest, most-recurring single-dimension
version (field_position alone, no situational filter) plus the
strongest filtered version (field_position + outdoor_only, since that
appeared multiple times and is a stable, non-early-season filter) on an
independent split before considering a Phase 2 spend.
"""
import pandas as pd

CANDIDATES = [
    ("field_position, all_games, pct=0.075", "field_position", "all_games", 0.075),
    ("field_position, outdoor_only, pct=0.075", "field_position", "outdoor_only", 0.075),
    ("field_position, low_wind, pct=0.075", "field_position", "low_wind", 0.075),
]

SPLITS = [2023, 2024]  # test years, training on immediately prior year


def bucket_fn(df):
    return df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]


def filter_fn(df, name):
    if name == "all_games":
        return pd.Series(True, index=df.index)
    if name == "outdoor_only":
        return df["is_dome"] != True
    if name == "low_wind":
        return df["wind_mph"] < 10
    raise ValueError(name)


def evaluate(full_df, test_year, filter_name, pct):
    train_df = full_df[full_df["season"] == test_year - 1].copy()
    test_df = full_df[full_df["season"] == test_year].copy()

    train_df["bucket_val"] = bucket_fn(train_df)
    test_df["bucket_val"] = bucket_fn(test_df)
    train_df = train_df.dropna(subset=["bucket_val"])
    test_df = test_df.dropna(subset=["bucket_val"])

    train_df["decile"] = pd.qcut(train_df["bucket_val"], 10, labels=False, duplicates="drop")
    bucket_avg = train_df.groupby("decile")["market_total_open"].mean()

    bins = pd.qcut(train_df["bucket_val"], 10, retbins=True, duplicates="drop")[1]
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

    for label, _, filter_name, pct in CANDIDATES:
        print(f"\n=== {label} ===")
        for test_year in SPLITS:
            result = evaluate(full_df, test_year, filter_name, pct)
            if result is None:
                print(f"  {test_year}: insufficient data")
                continue
            wins, total = result
            rate = wins / total * 100
            marker = " <-- above breakeven" if rate >= 52.4 else ""
            print(f"  {test_year}: {wins}/{total} = {rate:.1f}%{marker}")


if __name__ == "__main__":
    run()