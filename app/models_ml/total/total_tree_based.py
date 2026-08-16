"""
Tree-based (XGBoost) regression for Total - can capture non-linear
interactions (pace x efficiency, not just additive) automatically,
unlike the linear Ridge approach tried twice already. Uses the FULL
feature set available (not just combined/summed - trees handle
correlated/raw features more gracefully than linear regression, so no
need to pre-combine home/away stats by hand).

Phase 1 only: train 2021-2023, validate 2024, second split validating
2023. 2025 still reserved.
"""
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

SPLITS = [
    ("train 2021-2023, validate 2024", 2021, 2023, 2024),
    ("train 2021-2022, validate 2023", 2021, 2022, 2023),
]
GAP_THRESHOLDS = [2, 3, 5, 7]

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]
MARKET_COLUMNS_EXCEPT_TOTAL_OPEN = [
    "market_spread", "market_spread_open", "market_total",
    "market_home_moneyline", "market_away_moneyline",
]

TREE_PARAMS = dict(
    n_estimators=200, max_depth=3, learning_rate=0.02,
    subsample=0.7, colsample_bytree=0.6,
    reg_alpha=0.5, reg_lambda=2.0, min_child_weight=5,
)


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    exclude = NON_FEATURE_COLUMNS + ID_COLUMNS + MARKET_COLUMNS_EXCEPT_TOTAL_OPEN + \
              ["market_total_open"]  # keep total_open OUT of features - that's the target comparison, not an input
    feature_cols = [c for c in df.columns if c not in exclude]

    return df, df[feature_cols], df["actual_total"], feature_cols


def evaluate(full_df, train_start, train_end, val_year):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    val_df = full_df[full_df["season"] == val_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_val, X_val, y_val, _ = prepare(val_df)

    model = xgb.XGBRegressor(random_state=42, **TREE_PARAMS)
    model.fit(X_train, y_train)

    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)
    train_mae = mean_absolute_error(y_train, train_preds)
    val_mae = mean_absolute_error(y_val, val_preds)

    df_val = df_val.copy()
    df_val["predicted_total"] = val_preds
    df_val["gap"] = df_val["predicted_total"] - df_val["market_total_open"]
    df_val["bet_over"] = df_val["gap"] > 0
    df_val["actual_over"] = df_val["actual_total"] > df_val["market_total_open"]
    df_val = df_val[df_val["actual_total"] != df_val["market_total_open"]]

    return df_val, train_mae, val_mae, feature_cols, model


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    for label, start, end, val in SPLITS:
        df_val, train_mae, val_mae, feature_cols, model = evaluate(full_df, start, end, val)
        gap = val_mae - train_mae
        print(f"\n=== {label} ===")
        print(f"  Train MAE: {train_mae:.2f} | Val MAE: {val_mae:.2f} | Gap: {gap:.2f}")

        for threshold in GAP_THRESHOLDS:
            confident = df_val[df_val["gap"].abs() >= threshold]
            if len(confident) == 0:
                print(f"  Gap>={threshold}: no bets")
                continue
            correct = confident["bet_over"] == confident["actual_over"]
            win_rate = correct.mean() * 100
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {len(confident)} bets, {win_rate:.1f}% win rate{marker}")

    df_val, _, _, feature_cols, model = evaluate(full_df, 2021, 2023, 2024)
    print("\n=== Top 15 feature importances (primary split) ===")
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    for feat, imp in importances.head(15).items():
        print(f"  {feat}: {imp:.4f}")


if __name__ == "__main__":
    run()