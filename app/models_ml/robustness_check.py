"""
Standard robustness checks - run on every trained model, not just when
something looks suspicious. Catches overfitting and hidden bias that a
single MAE number can hide.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
TARGET_COLUMN = "actual_spread"


def load_and_prepare(path):
    df = pd.read_csv(path)
    df = df[df[TARGET_COLUMN].notna()].copy()
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return df, df[feature_cols], df[TARGET_COLUMN], feature_cols


def run_robustness_check():
    df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation.csv")
    df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout.csv")

    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model.fit(X_train, y_train)

    train_preds = model.predict(X_train)
    test_preds = model.predict(X_test)

    print("=== Overfitting check: training error vs holdout error ===")
    train_mae = mean_absolute_error(y_train, train_preds)
    test_mae = mean_absolute_error(y_test, test_preds)
    print(f"  Training MAE: {train_mae:.2f}")
    print(f"  Holdout MAE:  {test_mae:.2f}")
    gap = test_mae - train_mae
    print(f"  Gap: {gap:.2f} points ({'CONCERNING - large gap suggests overfitting' if gap > 5 else 'reasonable'})")

    print("\n=== Residual distribution (holdout set, market-line games only) ===")
    market_mask = df_test["market_spread"].notna()
    residuals = (y_test[market_mask] - test_preds[market_mask])
    print(f"  Mean residual (bias check - should be near 0): {residuals.mean():.2f}")
    print(f"  Std dev of residuals: {residuals.std():.2f}")
    print(f"  Median absolute error: {residuals.abs().median():.2f}")
    print(f"  90th percentile absolute error: {residuals.abs().quantile(0.90):.2f}")
    print(f"  Worst 5 predictions (largest errors):")
    worst = residuals.abs().nlargest(5)
    for idx in worst.index:
        actual = y_test.loc[idx]
        pred = test_preds[df_test.index.get_loc(idx)]
        print(f"    game_id={df_test.loc[idx, 'game_id']}: actual={actual:.0f}, predicted={pred:.1f}, error={residuals.loc[idx]:.1f}")

    print("\n=== Directional bias check: does the model favor home or away systematically? ===")
    home_favored_actual = y_test[market_mask] > 0
    print(f"  When home actually won by more (positive actual_spread): "
          f"avg residual = {residuals[home_favored_actual].mean():.2f}")
    print(f"  When away actually won or covered (negative actual_spread): "
          f"avg residual = {residuals[~home_favored_actual].mean():.2f}")


if __name__ == "__main__":
    run_robustness_check()