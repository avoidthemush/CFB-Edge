"""
Trains the Spread VALIDATION model - 2021-2024 training data, evaluated
against the 2025 holdout. This model is never used for real predictions
(per V2_MODEL_PLAN.md naming convention) - it exists purely to prove the
feature set and approach work before committing to a production model.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Columns that must NEVER be model inputs - identifiers, or anything
# that leaks the actual outcome
NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]

TARGET_COLUMN = "actual_spread"


def load_and_prepare(path):
    df = pd.read_csv(path)

    # Only train/evaluate on rows where we actually have an outcome
    df = df[df[TARGET_COLUMN].notna()].copy()

    # Convert True/False strings (from CSV round-trip) to real booleans/ints
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    X = df[feature_cols]
    y = df[TARGET_COLUMN]
    return X, y, feature_cols


def train_and_evaluate():
    print("Loading training data (2021-2024)...")
    X_train, y_train, feature_cols = load_and_prepare("training_data_validation.csv")
    print(f"  {len(X_train)} training rows, {len(feature_cols)} features")

    print("\nLoading holdout data (2025)...")
    X_test, y_test, _ = load_and_prepare("training_data_2025_holdout.csv")
    print(f"  {len(X_test)} holdout rows")

    print("\nTraining XGBoost regressor...")
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        enable_categorical=False,
    )
    model.fit(X_train, y_train)

    print("\nEvaluating against 2025 holdout...")
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"  MAE: {mae:.2f} points")
    print(f"  RMSE: {rmse:.2f} points")

    # Compare against just always predicting the market's own spread -
    # the real bar to clear, not just "better than guessing zero"
    market_available = X_test["market_spread"].notna()
    if market_available.sum() > 0:
        market_mae = mean_absolute_error(
            y_test[market_available], -X_test.loc[market_available, "market_spread"]
        )
        model_mae_when_market_available = mean_absolute_error(
            y_test[market_available], preds[market_available]
        )
        print(f"\n  On the {market_available.sum()} rows with a market line available:")
        print(f"    Market's own MAE: {market_mae:.2f} points")
        print(f"    Model's MAE: {model_mae_when_market_available:.2f} points")

    print("\nTop 15 most important features:")
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    for feat, imp in importances.head(15).items():
        print(f"  {feat}: {imp:.4f}")

    model.save_model("spread_validation_model.json")
    print("\nModel saved to spread_validation_model.json")

    return model, mae, rmse


if __name__ == "__main__":
    train_and_evaluate()