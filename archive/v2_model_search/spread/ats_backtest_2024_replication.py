"""
Replication check: same fundamentals-vs-opening-line test as
ats_backtest_vs_open.py, but on 2024 as an independent sample - train on
2021-2022 only, test on 2024. If the monotonic win-rate-improves-with-
edge-size pattern shows up here too, that's real corroborating evidence
the 2025 result wasn't a fluke. If it doesn't replicate, treat the 2025
result as likely noise, not a confirmed edge.
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
    n_estimators=80, max_depth=2, learning_rate=0.05,
    subsample=0.7, colsample_bytree=0.7,
    reg_alpha=1.0, reg_lambda=3.0, min_child_weight=8,
)

EDGE_THRESHOLDS = [0, 1, 2, 3, 5, 7]
VIG_PRICE = -110


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


def run():
    full = pd.read_csv("training_data_validation_fbs.csv")

    train_df = full[full["season"] <= 2022]
    test_df = full[full["season"] == 2024]

    df_train, X_train, y_train, feature_cols = load_and_prepare(train_df)
    df_test, X_test, y_test, _ = load_and_prepare(test_df)

    print(f"REPLICATION CHECK: train 2021-2022 ({len(X_train)} rows), test 2024 ({len(X_test)} rows)\n")

    model = xgb.XGBRegressor(random_state=42, **BEST_PARAMS)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    df_test = df_test.copy()
    df_test["predicted_margin"] = preds
    df_test["open_implied_margin"] = -df_test["market_spread_open"]
    df_test["edge_vs_open"] = df_test["predicted_margin"] - df_test["open_implied_margin"]
    df_test["actual_margin"] = y_test.values

    win_unit = units_won_per_bet()

    for threshold in EDGE_THRESHOLDS:
        bets = df_test[df_test["edge_vs_open"].abs() >= threshold].copy()
        if len(bets) == 0:
            print(f"Edge >= {threshold}: no qualifying bets")
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
        pushes = (bets["result"] == "push").sum()
        decided = wins + losses
        win_rate = wins / decided * 100 if decided > 0 else 0
        units = wins * win_unit - losses * 1.0
        roi = units / decided * 100 if decided > 0 else 0

        print(f"Edge >= {threshold} points vs OPEN: {len(bets)} bets ({wins}W-{losses}L-{pushes}P)")
        print(f"  Win rate: {win_rate:.1f}% (breakeven 52.4%)  |  Units: {units:+.2f}u  |  ROI: {roi:+.1f}%")
        print()


if __name__ == "__main__":
    run()