"""
Structural alternative to the classifier approach: predicts actual_total
directly (regression), then compares to market_total_open. Confidence
is the SIZE of the gap between our prediction and the market's number,
not a probability - tested across several thresholds. Same Phase 1
discipline (train 2021-2023/validate 2024, plus a second split for
stability), same combined/additive feature framing as the classifier
version, for a fair, apples-to-apples comparison.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error

GAP_THRESHOLDS = [2, 3, 5, 7, 10]

SPLITS = [
    ("train 2021-2023, validate 2024", 2021, 2023, 2024),
    ("train 2021-2022, validate 2023", 2021, 2022, 2023),
]


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
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

    return df, df[feature_cols], df["actual_total"], feature_cols


def evaluate(full_df, train_start, train_end, val_year):
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

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train)

    train_preds = model.predict(X_train_scaled)
    val_preds = model.predict(X_val_scaled)

    train_mae = mean_absolute_error(y_train, train_preds)
    val_mae = mean_absolute_error(y_val, val_preds)

    df_val = df_val.copy()
    df_val["predicted_total"] = val_preds
    df_val["gap"] = df_val["predicted_total"] - df_val["market_total_open"]
    df_val["bet_over"] = df_val["gap"] > 0
    df_val["actual_over"] = df_val["actual_total"] > df_val["market_total_open"]
    df_val = df_val[df_val["actual_total"] != df_val["market_total_open"]]  # drop pushes

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

    # Coefficients from the primary split, for a quick sanity read
    df_val, _, _, feature_cols, model = evaluate(full_df, 2021, 2023, 2024)
    print("\n=== Feature coefficients (primary split) ===")
    coefs = pd.Series(model.coef_, index=feature_cols).sort_values(key=abs, ascending=False)
    for feat, coef in coefs.items():
        direction = "-> favors OVER" if coef > 0 else "-> favors UNDER"
        print(f"  {feat}: {coef:+.3f} {direction}")


if __name__ == "__main__":
    run()