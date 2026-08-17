"""
Re-tests for edge using a fundamentally different, less circular setup:
- Model trained WITHOUT any market features at all (pure fundamentals)
- Edge measured against the OPENING line, not closing - this tests
  whether our football signal identifies value before the market fully
  absorbs information, which is the realistic betting scenario (you bet
  against a currently-posted line, not the final closing number).
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


def load_and_prepare(path, drop_market=True):
    df = pd.read_csv(path)
    df = df[df[TARGET_COLUMN].notna()].copy()
    df = df[df["market_spread_open"].notna()].copy()  # need an opening line to test against
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    exclude = NON_FEATURE_COLUMNS + (MARKET_COLUMNS if drop_market else [])
    feature_cols = [c for c in df.columns if c not in exclude]
    return df, df[feature_cols], df[TARGET_COLUMN], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    return 100 / abs(vig_price)


def run():
    df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation_fbs.csv", drop_market=True)
    df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout_fbs.csv", drop_market=True)

    print(f"Fundamentals-only model (NO market features at all)")
    print(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows\n")

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