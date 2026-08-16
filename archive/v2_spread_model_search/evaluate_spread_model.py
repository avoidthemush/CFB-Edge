"""
Deeper evaluation of the Spread validation model:
1. Performance restricted to games with a real market line (fair comparison)
2. Performance with market features EXCLUDED entirely (tests whether the
   model has real standalone football signal, or is just echoing the market)
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
MARKET_COLUMNS = [
    "market_spread", "market_spread_open", "market_total", "market_total_open",
    "market_home_moneyline", "market_away_moneyline",
]
TARGET_COLUMN = "actual_spread"


def load_and_prepare(path, drop_market=False):
    df = pd.read_csv(path)
    df = df[df[TARGET_COLUMN].notna()].copy()

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    exclude = NON_FEATURE_COLUMNS + (MARKET_COLUMNS if drop_market else [])
    feature_cols = [c for c in df.columns if c not in exclude]
    X = df[feature_cols]
    y = df[TARGET_COLUMN]
    return df, X, y, feature_cols


def run_comparison():
    print("=== Test 1: fundamentals-only model (no market features at all) ===")
    df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation.csv", drop_market=True)
    df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout.csv", drop_market=True)

    model_no_market = xgb.XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model_no_market.fit(X_train, y_train)
    preds_no_market = model_no_market.predict(X_test)
    mae_no_market = mean_absolute_error(y_test, preds_no_market)
    print(f"  Overall MAE (no market features): {mae_no_market:.2f} points")

    market_mask = df_test["market_spread"].notna()
    mae_no_market_fbs = mean_absolute_error(y_test[market_mask], preds_no_market[market_mask])
    print(f"  MAE on real-market-line games only: {mae_no_market_fbs:.2f} points "
          f"(n={market_mask.sum()})")

    print("\n=== Test 2: full model (with market features), same subset for fair comparison ===")
    df_train2, X_train2, y_train2, _ = load_and_prepare("training_data_validation.csv", drop_market=False)
    df_test2, X_test2, y_test2, _ = load_and_prepare("training_data_2025_holdout.csv", drop_market=False)

    model_full = xgb.XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model_full.fit(X_train2, y_train2)
    preds_full = model_full.predict(X_test2)

    mae_full_fbs = mean_absolute_error(y_test2[market_mask], preds_full[market_mask])
    market_own_mae = mean_absolute_error(y_test2[market_mask], -df_test2.loc[market_mask, "market_spread"])

    print(f"  MAE on real-market-line games only: {mae_full_fbs:.2f} points (n={market_mask.sum()})")
    print(f"  Market's own MAE on same games: {market_own_mae:.2f} points")

    print("\n=== Summary ===")
    print(f"  Fundamentals-only, real games:  {mae_no_market_fbs:.2f} MAE")
    print(f"  With market feature, real games: {mae_full_fbs:.2f} MAE")
    print(f"  Market itself, real games:       {market_own_mae:.2f} MAE")


if __name__ == "__main__":
    run_comparison()