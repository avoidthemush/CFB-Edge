"""
Same Spread validation model, but with sample weighting by outcome
magnitude - addresses the blowout-compression/sign-flip pattern found
in robustness_check.py. Compares directly against the unweighted
baseline, including specifically on CLOSE games (the ones that actually
matter for finding real betting edges - blowouts rarely produce
actionable disagreement with the market).
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


def train_model(X_train, y_train, sample_weight=None):
    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model.fit(X_train, y_train, sample_weight=sample_weight)
    return model


def evaluate(model, df_test, X_test, y_test, label):
    preds = model.predict(X_test)
    market_mask = df_test["market_spread"].notna()

    overall_mae = mean_absolute_error(y_test, preds)

    # Sign-flip rate: model picked the wrong winner entirely
    actual_home_win = y_test > 0
    pred_home_win = preds > 0
    sign_flips = (actual_home_win != pred_home_win).sum()
    sign_flip_rate = sign_flips / len(y_test) * 100

    # Close games only - |actual_spread| <= 10, the ones that matter for real edges
    close_mask = market_mask & (y_test.abs() <= 10)
    close_mae = mean_absolute_error(y_test[close_mask], preds[close_mask]) if close_mask.sum() > 0 else None

    blowout_mask = market_mask & (y_test.abs() > 21)
    blowout_mae = mean_absolute_error(y_test[blowout_mask], preds[blowout_mask]) if blowout_mask.sum() > 0 else None

    print(f"\n=== {label} ===")
    print(f"  Overall MAE: {overall_mae:.2f}")
    print(f"  Sign-flip rate (wrong winner predicted): {sign_flip_rate:.1f}% ({sign_flips}/{len(y_test)})")
    print(f"  Close games (|spread|<=10) MAE: {close_mae:.2f} (n={close_mask.sum()})" if close_mae else "  No close games in sample")
    print(f"  Blowout games (|spread|>21) MAE: {blowout_mae:.2f} (n={blowout_mask.sum()})" if blowout_mae else "  No blowout games in sample")

    return preds


def run():
    df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation.csv")
    df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout.csv")

    print("Training baseline (unweighted)...")
    baseline_model = train_model(X_train, y_train)
    evaluate(baseline_model, df_test, X_test, y_test, "BASELINE (unweighted)")

    print("\nTraining weighted (samples weighted by |actual_spread|)...")
    weights = 1 + y_train.abs() / 20  # blowouts get up to ~4-5x weight of a close game
    weighted_model = train_model(X_train, y_train, sample_weight=weights)
    evaluate(weighted_model, df_test, X_test, y_test, "WEIGHTED (by outcome magnitude)")


if __name__ == "__main__":
    run()