"""
FIRST AND ONLY look at the 2025 holdout for the Spread validation model.
Trains on the full 2021-2023 + 2024 internal set (everything except
2025) using the winning config from tune_spread_fbs.py ("very
conservative"), then evaluates once against 2025 - genuinely sealed
until now. This result is what determines whether the Spread validation
model is considered proven, per V2_MODEL_PLAN.md.
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


def load_and_prepare(path):
    df = pd.read_csv(path)
    df = df[df[TARGET_COLUMN].notna()].copy()
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return df, df[feature_cols], df[TARGET_COLUMN], feature_cols


def run():
    df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation_fbs.csv")
    df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout_fbs.csv")

    print(f"Training on ALL of 2021-2024 (FBS-only): {len(X_train)} rows")
    print(f"Evaluating on SEALED 2025 holdout (FBS-only): {len(X_test)} rows\n")

    model = xgb.XGBRegressor(random_state=42, **BEST_PARAMS)
    model.fit(X_train, y_train)

    train_preds = model.predict(X_train)
    test_preds = model.predict(X_test)

    train_mae = mean_absolute_error(y_train, train_preds)
    test_mae = mean_absolute_error(y_test, test_preds)
    gap = test_mae - train_mae

    close_mask = y_test.abs() <= 10
    blowout_mask = y_test.abs() > 21

    print(f"Train MAE: {train_mae:.2f}")
    print(f"2025 Holdout MAE: {test_mae:.2f}")
    print(f"Gap: {gap:.2f} ({'healthy' if abs(gap) < 3 else 'CONCERNING'})")

    print(f"\nClose games MAE (n={close_mask.sum()}): {mean_absolute_error(y_test[close_mask], test_preds[close_mask]):.2f}")
    print(f"Blowout games MAE (n={blowout_mask.sum()}): {mean_absolute_error(y_test[blowout_mask], test_preds[blowout_mask]):.2f}")

    market_mae = mean_absolute_error(y_test, -df_test["market_spread"])
    print(f"\nMarket's own MAE on same games: {market_mae:.2f}")
    print(f"Model vs market gap: {test_mae - market_mae:+.2f} points ({'model wins' if test_mae < market_mae else 'market still ahead'})")

    model.save_model("spread_validation_model_final.json")
    print("\nModel saved to spread_validation_model_final.json")


if __name__ == "__main__":
    run()