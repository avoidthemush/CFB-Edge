"""
Confirms whether Total's baseline coefficient directions are stable
across TWO independent internal splits, and separately tunes
regularization strength (C) for Total specifically - we've been reusing
Spread's C=0.1 without ever testing whether that's right for a
different target. Still Phase 1 only - 2025 untouched.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

CONFIDENCE_THRESHOLD = 0.60
C_VALUES = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]

SPLITS = [
    ("train 2021-2023, validate 2024", 2021, 2023, 2024),
    ("train 2021-2022, validate 2023", 2021, 2022, 2023),
]


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["over_covers"] = (df["actual_total"] > df["market_total_open"]).astype(int)
    df = df[df["actual_total"] != df["market_total_open"]]

    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})

    df["combined_off_success_rate"] = df["home_off_success_rate"] + df["away_off_success_rate"]
    df["combined_off_explosiveness"] = df["home_off_explosiveness"] + df["away_off_explosiveness"]
    df["combined_off_ppa"] = df["home_off_ppa"] + df["away_off_ppa"]
    df["combined_def_ppa"] = df["home_def_ppa"] + df["away_def_ppa"]
    df["combined_def_points_per_opp"] = df["home_def_points_per_opportunity"] + df["away_def_points_per_opportunity"]
    df["combined_off_points_per_opp"] = df["home_off_points_per_opportunity"] + df["away_off_points_per_opportunity"]
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
    df["combined_pass_rate"] = df["home_pass_rate"] + df["away_pass_rate"]
    df["combined_off_third_down_pct"] = df["home_off_third_down_pct"] + df["away_off_third_down_pct"]
    df["combined_def_third_down_pct_allowed"] = df["home_def_third_down_pct_allowed"] + df["away_def_third_down_pct_allowed"]
    df["combined_turnover_margin_abs_gap"] = (df["home_turnover_margin"] - df["away_turnover_margin"]).abs()
    df["combined_field_position_predicted_points"] = (
        df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]
    )

    feature_cols = [
        "combined_off_success_rate", "combined_off_explosiveness", "combined_off_ppa",
        "combined_def_ppa", "combined_def_points_per_opp", "combined_off_points_per_opp",
        "combined_pace", "combined_pass_rate", "combined_off_third_down_pct",
        "combined_def_third_down_pct_allowed", "combined_turnover_margin_abs_gap",
        "combined_field_position_predicted_points",
        "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome",
    ]

    return df, df[feature_cols], df["over_covers"], feature_cols


def evaluate(full_df, train_start, train_end, val_year, C):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    val_df = full_df[full_df["season"] == val_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_val, X_val, y_val, _ = prepare(val_df)

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = LogisticRegression(C=C, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_val_scaled)[:, 1]

    bet_over = probs >= 0.5
    confidence = np.where(bet_over, probs, 1 - probs)
    bet_mask = confidence >= CONFIDENCE_THRESHOLD

    win_rate = None
    if bet_mask.sum() > 0:
        actual = y_val.values[bet_mask].astype(bool)
        predicted = bet_over[bet_mask]
        win_rate = (predicted == actual).mean() * 100

    coefs = pd.Series(model.coef_[0], index=feature_cols)
    return win_rate, bet_mask.sum(), coefs


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    print("=== PART 1: Regularization strength search (C), using original split ===\n")
    for C in C_VALUES:
        win_rate, n_bets, _ = evaluate(full_df, 2021, 2023, 2024, C)
        if win_rate is not None:
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  C={C}: {win_rate:.1f}% ({n_bets} bets){marker}")
        else:
            print(f"  C={C}: no confident bets")

    print("\n\n=== PART 2: Coefficient stability across two independent splits (C=0.1) ===\n")
    all_coefs = {}
    for label, start, end, val in SPLITS:
        win_rate, n_bets, coefs = evaluate(full_df, start, end, val, C=0.1)
        all_coefs[label] = coefs
        wr_str = f"{win_rate:.1f}% ({n_bets} bets)" if win_rate is not None else "no confident bets"
        print(f"{label}: {wr_str}")

    print("\n=== Direction agreement between the two splits ===")
    labels = list(all_coefs.keys())
    coefs_a, coefs_b = all_coefs[labels[0]], all_coefs[labels[1]]
    agree_count = 0
    for feat in coefs_a.index:
        sign_a = np.sign(coefs_a[feat])
        sign_b = np.sign(coefs_b[feat])
        agrees = sign_a == sign_b
        agree_count += agrees
        marker = "AGREE" if agrees else "DISAGREE"
        print(f"  {feat}: split1={coefs_a[feat]:+.3f}, split2={coefs_b[feat]:+.3f} - {marker}")

    print(f"\n{agree_count}/{len(coefs_a)} features agree on direction across both splits")


if __name__ == "__main__":
    run()