"""
Tests L1 (Lasso) regularization - true automatic feature selection,
where the optimizer zeroes out weak features during training rather than
us manually guessing which categories to remove. Also grid-searches
regularization strength (C), which we held fixed at 0.1 all night without
ever testing alternatives. Uses INTERNAL split only (train early years,
validate on 2024) - 2025 stays untouched during this search phase.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]
RECRUITING_COLS = [
    "home_recruiting_rank", "away_recruiting_rank", "diff_recruiting_rank",
    "home_recruiting_points", "away_recruiting_points", "diff_recruiting_points",
    "home_off_new_talent_impact", "away_off_new_talent_impact", "diff_off_new_talent_impact",
    "home_def_new_talent_impact", "away_def_new_talent_impact", "diff_def_new_talent_impact",
    "talent_edge_early_season", "recruiting_edge_early_season",
]

C_VALUES = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
CONFIDENCE_THRESHOLD = 0.60


def prepare(df):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    exclude = NON_FEATURE_COLUMNS + ID_COLUMNS + RECRUITING_COLS + \
              ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in df.columns if c not in exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def evaluate_config(X_train, y_train, X_val, y_val, df_val, penalty, C):
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    solver = "liblinear" if penalty == "l1" else "lbfgs"
    model = LogisticRegression(penalty=penalty, C=C, solver=solver, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)

    probs = model.predict_proba(X_val_scaled)[:, 1]
    confident = (probs >= CONFIDENCE_THRESHOLD) | (probs <= (1 - CONFIDENCE_THRESHOLD))

    if confident.sum() == 0:
        return None

    bet_home = probs[confident] >= CONFIDENCE_THRESHOLD
    actual_home = y_val.values[confident].astype(bool)
    win_rate = (bet_home == actual_home).mean() * 100

    n_nonzero = np.sum(np.abs(model.coef_[0]) > 1e-6)

    return win_rate, confident.sum(), n_nonzero


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")

    train_df = full_df[full_df["season"] <= 2022]
    val_df = full_df[full_df["season"] == 2023]

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_val, X_val, y_val, _ = prepare(val_df)

    print(f"Internal search: train 2015-2022 ({len(X_train)} rows), validate 2023 ({len(X_val)} rows)")
    print(f"Total features available: {len(feature_cols)}\n")

    print(f"{'Penalty':<10}{'C':>8}{'Win rate':>12}{'# bets':>10}{'Features used':>16}")
    for penalty in ["l1", "l2"]:
        for C in C_VALUES:
            result = evaluate_config(X_train, y_train, X_val, y_val, df_val, penalty, C)
            if result is None:
                print(f"{penalty:<10}{C:>8}{'no bets':>12}")
                continue
            win_rate, n_bets, n_features = result
            marker = " *" if win_rate >= 52.4 else ""
            print(f"{penalty:<10}{C:>8}{win_rate:>11.1f}%{n_bets:>10}{n_features:>16}{marker}")


if __name__ == "__main__":
    run()