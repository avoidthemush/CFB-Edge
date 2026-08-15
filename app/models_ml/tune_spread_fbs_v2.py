"""
Hyperparameter comparison against the expanded 2015-2024 FBS-only
dataset. Train 2015-2023, internal validation 2024. 2025 stays sealed.
"""
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
TARGET_COLUMN = "actual_spread"

CANDIDATES = {
    "baseline (original settings)": dict(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
    ),
    "shallower + fewer trees": dict(
        n_estimators=100, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
    ),
    "shallower + more regularization": dict(
        n_estimators=150, max_depth=3, learning_rate=0.03,
        subsample=0.7, colsample_bytree=0.7,
        reg_alpha=1.0, reg_lambda=2.0, min_child_weight=5,
    ),
    "very conservative (prior winner)": dict(
        n_estimators=80, max_depth=2, learning_rate=0.05,
        subsample=0.7, colsample_bytree=0.7,
        reg_alpha=1.0, reg_lambda=3.0, min_child_weight=8,
    ),
    "moderate depth, strong reg": dict(
        n_estimators=200, max_depth=3, learning_rate=0.02,
        subsample=0.7, colsample_bytree=0.6,
        reg_alpha=0.5, reg_lambda=2.0, min_child_weight=5,
    ),
    "more trees, low lr (more data available now)": dict(
        n_estimators=400, max_depth=3, learning_rate=0.02,
        subsample=0.75, colsample_bytree=0.7,
        reg_alpha=0.5, reg_lambda=1.5, min_child_weight=4,
    ),
}


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
    df_full, X_full, y_full, feature_cols = load_and_prepare("training_data_validation_v2_fbs.csv")

    train_mask = df_full["season"] <= 2023
    val_mask = df_full["season"] == 2024

    X_train, y_train = X_full[train_mask], y_full[train_mask]
    X_val, y_val, df_val = X_full[val_mask], y_full[val_mask], df_full[val_mask]

    print(f"Train: {len(X_train)} rows | Validation: {len(X_val)} rows\n")

    close_mask = y_val.abs() <= 10
    blowout_mask = y_val.abs() > 21

    results = []

    for name, params in CANDIDATES.items():
        model = xgb.XGBRegressor(random_state=42, **params)
        model.fit(X_train, y_train)

        train_preds = model.predict(X_train)
        val_preds = model.predict(X_val)

        train_mae = mean_absolute_error(y_train, train_preds)
        val_mae = mean_absolute_error(y_val, val_preds)
        close_mae = mean_absolute_error(y_val[close_mask], val_preds[close_mask])
        blowout_mae = mean_absolute_error(y_val[blowout_mask], val_preds[blowout_mask])
        gap = val_mae - train_mae

        results.append((name, train_mae, val_mae, close_mae, blowout_mae, gap))

        print(f"=== {name} ===")
        print(f"  Train MAE: {train_mae:.2f} | Val MAE: {val_mae:.2f} | Gap: {gap:.2f}")
        print(f"  Close games MAE: {close_mae:.2f}")
        print(f"  Blowout games MAE: {blowout_mae:.2f}\n")

    print("=== Summary, sorted by close-game MAE ===")
    for name, train_mae, val_mae, close_mae, blowout_mae, gap in sorted(results, key=lambda r: r[3]):
        print(f"  {name}: close={close_mae:.2f}, blowout={blowout_mae:.2f}, gap={gap:.2f}")


if __name__ == "__main__":
    run()