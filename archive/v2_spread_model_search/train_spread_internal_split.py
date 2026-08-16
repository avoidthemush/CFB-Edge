"""
Internal validation split for tuning/refinement work - train 2021-2023,
validate against 2024. The 2025 holdout is deliberately NOT touched here,
to preserve its integrity as a genuine, un-peeked-at final test. Only
come back to 2025 once refinement is actually finished.
"""
import pandas as pd
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


def evaluate(model, df, X, y, label):
    preds = model.predict(X)
    market_mask = df["market_spread"].notna()
    close_mask = market_mask & (y.abs() <= 10)
    blowout_mask = market_mask & (y.abs() > 21)

    print(f"\n=== {label} ===")
    print(f"  Overall MAE: {mean_absolute_error(y, preds):.2f}")
    if close_mask.sum() > 0:
        print(f"  Close games MAE (n={close_mask.sum()}): {mean_absolute_error(y[close_mask], preds[close_mask]):.2f}")
    if blowout_mask.sum() > 0:
        print(f"  Blowout games MAE (n={blowout_mask.sum()}): {mean_absolute_error(y[blowout_mask], preds[blowout_mask]):.2f}")


def run():
    df_full, X_full, y_full, feature_cols = load_and_prepare("training_data_validation_fbs.csv")

    train_mask = df_full["season"] <= 2023
    val_mask = df_full["season"] == 2024

    X_train, y_train = X_full[train_mask], y_full[train_mask]
    X_val, y_val, df_val = X_full[val_mask], y_full[val_mask], df_full[val_mask]

    print(f"Internal train: {len(X_train)} rows (2021-2023)")
    print(f"Internal validation: {len(X_val)} rows (2024)")

    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model.fit(X_train, y_train)

    evaluate(model, df_val, X_val, y_val, "Baseline params, internal validation (2024)")


if __name__ == "__main__":
    run()