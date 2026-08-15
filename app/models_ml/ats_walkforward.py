"""
Walk-forward ATS validation: instead of one train/test split, tests
the fundamentals-vs-opening-line approach across SEVERAL independent
year-pairs. A real edge should show a consistent pattern across most/all
of these; noise will look different (or contradictory) each time - this
is the real payoff of extending history back to 2015, not a bigger
single holdout.
"""
import pandas as pd
import xgboost as xgb

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
MARKET_COLUMNS = [
    "market_spread", "market_spread_open", "market_total", "market_total_open",
    "market_home_moneyline", "market_away_moneyline",
]
TARGET_COLUMN = "actual_spread"

BEST_PARAMS = dict(
    n_estimators=200, max_depth=3, learning_rate=0.02,
    subsample=0.7, colsample_bytree=0.6,
    reg_alpha=0.5, reg_lambda=2.0, min_child_weight=5,
)

EDGE_THRESHOLDS = [0, 2, 3, 5, 7]
VIG_PRICE = -110

# Each fold: (train_start, train_end, test_year) - test year always
# strictly after training years, walking forward through time
FOLDS = [
    (2015, 2017, 2018),
    (2015, 2018, 2019),
    (2015, 2019, 2020),
    (2015, 2020, 2021),
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def load_and_prepare(df):
    df = df[df[TARGET_COLUMN].notna()].copy()
    df = df[df["market_spread_open"].notna()].copy()
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS + MARKET_COLUMNS]
    return df, df[feature_cols], df[TARGET_COLUMN], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    return 100 / abs(vig_price)


def run_fold(full_df, train_start, train_end, test_year):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    test_df = full_df[full_df["season"] == test_year]

    df_train, X_train, y_train, feature_cols = load_and_prepare(train_df)
    df_test, X_test, y_test, _ = load_and_prepare(test_df)

    if len(df_train) < 100 or len(df_test) < 30:
        return None

    model = xgb.XGBRegressor(random_state=42, **BEST_PARAMS)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    df_test = df_test.copy()
    df_test["predicted_margin"] = preds
    df_test["open_implied_margin"] = -df_test["market_spread_open"]
    df_test["edge_vs_open"] = df_test["predicted_margin"] - df_test["open_implied_margin"]
    df_test["actual_margin"] = y_test.values

    win_unit = units_won_per_bet()
    fold_results = {}

    for threshold in EDGE_THRESHOLDS:
        bets = df_test[df_test["edge_vs_open"].abs() >= threshold].copy()
        if len(bets) == 0:
            fold_results[threshold] = None
            continue

        def grade(row):
            if row["edge_vs_open"] > 0:
                if row["actual_margin"] > row["open_implied_margin"]:
                    return "win"
                elif row["actual_margin"] < row["open_implied_margin"]:
                    return "loss"
                return "push"
            else:
                if row["actual_margin"] < row["open_implied_margin"]:
                    return "win"
                elif row["actual_margin"] > row["open_implied_margin"]:
                    return "loss"
                return "push"

        bets["result"] = bets.apply(grade, axis=1)
        wins = (bets["result"] == "win").sum()
        losses = (bets["result"] == "loss").sum()
        decided = wins + losses
        win_rate = wins / decided * 100 if decided > 0 else 0
        units = wins * win_unit - losses * 1.0

        fold_results[threshold] = (len(bets), wins, losses, win_rate, units)

    return fold_results


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_fold_results = {}

    for train_start, train_end, test_year in FOLDS:
        print(f"\n=== Fold: train {train_start}-{train_end}, test {test_year} ===")
        result = run_fold(full_df, train_start, train_end, test_year)
        if result is None:
            print("  Skipped - insufficient data")
            continue
        all_fold_results[test_year] = result
        for threshold, data in result.items():
            if data is None:
                print(f"  Edge>={threshold}: no bets")
                continue
            n, wins, losses, win_rate, units = data
            print(f"  Edge>={threshold}: {n} bets, {win_rate:.1f}% win rate, {units:+.2f}u")

    print("\n\n=== SUMMARY: win rate by threshold, across all test years ===")
    for threshold in EDGE_THRESHOLDS:
        rates = []
        for year, result in all_fold_results.items():
            data = result.get(threshold)
            if data:
                rates.append((year, data[3], data[0]))
        if rates:
            print(f"\nEdge >= {threshold}:")
            for year, rate, n in rates:
                marker = " <-- above breakeven" if rate >= 52.4 else ""
                print(f"    {year}: {rate:.1f}% (n={n}){marker}")
            avg_rate = sum(r for _, r, _ in rates) / len(rates)
            above_breakeven = sum(1 for _, r, _ in rates if r >= 52.4)
            print(f"    AVG: {avg_rate:.1f}% | {above_breakeven}/{len(rates)} years above breakeven")


if __name__ == "__main__":
    run()