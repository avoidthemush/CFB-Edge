"""
Total v2.0 - baseline test using the FULL enriched feature set (pass/
rush rate, turnover margin, third-down rate, field position, offensive
points-per-opportunity all now available). Combined/additive framing
throughout - both teams' values summed, not differenced, since Total
is about the SUM of both scoring environments, not which team is better.

Phase 1: train 2021-2023, validate 2024. 2025 reserved for Phase 2.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

TRAIN_START, TRAIN_END, VALIDATE_YEAR = 2021, 2023, 2024
CONFIDENCE_THRESHOLD = 0.60


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


def evaluate(full_df):
    train_df = full_df[(full_df["season"] >= TRAIN_START) & (full_df["season"] <= TRAIN_END)]
    val_df = full_df[full_df["season"] == VALIDATE_YEAR]

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_val, X_val, y_val, _ = prepare(val_df)

    print(f"Train: {len(X_train)} games | Validate: {len(X_val)} games\n")

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_val_scaled)[:, 1]

    bet_over = probs >= 0.5
    confidence = np.where(bet_over, probs, 1 - probs)

    bet_mask = confidence >= CONFIDENCE_THRESHOLD
    print(f"Overall accuracy: {(bet_over == y_val.astype(bool)).mean()*100:.1f}%")
    print(f"Confident (>=60%) bets: {bet_mask.sum()}")

    if bet_mask.sum() > 0:
        actual = y_val.values[bet_mask].astype(bool)
        predicted = bet_over[bet_mask]
        correct = predicted == actual
        win_rate = correct.mean() * 100
        print(f"Win rate on confident bets: {win_rate:.1f}%")

    print("\n=== Feature coefficients (direction of effect) ===")
    coefs = pd.Series(model.coef_[0], index=feature_cols).sort_values(key=abs, ascending=False)
    for feat, coef in coefs.items():
        direction = "-> favors OVER" if coef > 0 else "-> favors UNDER"
        print(f"  {feat}: {coef:+.3f} {direction}")


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= VALIDATE_YEAR]
    evaluate(full_df)


if __name__ == "__main__":
    run()