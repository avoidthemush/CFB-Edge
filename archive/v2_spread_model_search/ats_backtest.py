"""
The real edge test for the Spread model: simulates ATS betting based on
model-vs-market disagreement, using the sealed 2025 holdout only.

Assumption: standard -110 odds both sides (CFBD's historical lines don't
include actual historical spread juice - this is an industry-standard
approximation, not verified historical pricing).

market_spread convention (confirmed earlier): negative = home favored.
So market's implied home margin = -market_spread.
Model's predicted margin is already in home-minus-away units.
edge = model_predicted_margin - market_implied_margin
  edge > 0 -> model thinks home outperforms the market's number -> bet HOME
  edge < 0 -> model thinks away outperforms the market's number -> bet AWAY
"""
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
TARGET_COLUMN = "actual_spread"

BEST_PARAMS = dict(
    n_estimators=80, max_depth=2, learning_rate=0.05,
    subsample=0.7, colsample_bytree=0.7,
    reg_alpha=1.0, reg_lambda=3.0, min_child_weight=8,
)

EDGE_THRESHOLDS = [0, 1, 2, 3, 5, 7]
VIG_PRICE = -110  # standard, not verified historical price


def load_and_prepare(path):
    df = pd.read_csv(path)
    df = df[df[TARGET_COLUMN].notna()].copy()
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return df, df[feature_cols], df[TARGET_COLUMN], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    # Risking 110 to win 100 -> win = +1.0 unit, loss = -1.1 units, on a 1-unit-to-win basis
    return 100 / abs(vig_price)


def run():
    df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation_fbs.csv")
    df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout_fbs.csv")

    model = xgb.XGBRegressor(random_state=42, **BEST_PARAMS)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    df_test = df_test.copy()
    df_test["predicted_margin"] = preds
    df_test["market_implied_margin"] = -df_test["market_spread"]
    df_test["edge"] = df_test["predicted_margin"] - df_test["market_implied_margin"]
    df_test["actual_margin"] = y_test.values

    win_unit = units_won_per_bet()

    print(f"Total games evaluated: {len(df_test)}")
    print(f"Assumed odds: {VIG_PRICE} both sides (win = +{win_unit:.3f}u, loss = -1.0u)\n")

    for threshold in EDGE_THRESHOLDS:
        bets = df_test[df_test["edge"].abs() >= threshold].copy()
        if len(bets) == 0:
            print(f"Edge >= {threshold}: no qualifying bets")
            continue

        def grade(row):
            if row["edge"] > 0:  # bet home
                if row["actual_margin"] > row["market_implied_margin"]:
                    return "win"
                elif row["actual_margin"] < row["market_implied_margin"]:
                    return "loss"
                return "push"
            else:  # bet away
                if row["actual_margin"] < row["market_implied_margin"]:
                    return "win"
                elif row["actual_margin"] > row["market_implied_margin"]:
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

        print(f"Edge >= {threshold} points: {len(bets)} bets ({wins}W-{losses}L-{pushes}P)")
        print(f"  Win rate: {win_rate:.1f}% (breakeven at -110 is 52.4%)")
        print(f"  Units: {units:+.2f}u | ROI: {roi:+.1f}%")
        print()


if __name__ == "__main__":
    run()