"""
Tests whether pace's declining year-over-year correlation with scoring
(confirmed: 0.194 in 2022 down to 0.021 in 2025) means recent-years-only
training beats training equally across all available years. If the true
relationship is drifting, diluting the model with stale 2021-2022 data
could be actively hurting 2025 performance specifically.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

GAP_THRESHOLDS = [3, 5, 7]

# Compare: training on ALL available years vs only the most RECENT years,
# both tested against 2025 (the freshest, most relevant test)
TRAINING_WINDOWS = [
    ("All years (2021-2024)", 2021, 2024),
    ("Recent only (2023-2024)", 2023, 2024),
    ("Most recent only (2024)", 2024, 2024),
]


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]

    feature_cols = ["combined_pace", "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome"]
    return df, df[feature_cols], df["actual_total"], feature_cols


def evaluate(train_df, test_df):
    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_test, X_test, y_test, _ = prepare(test_df)

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train)
    preds = model.predict(X_test_scaled)

    df_test = df_test.copy()
    df_test["gap"] = preds - df_test["market_total_open"]
    df_test["bet_over"] = df_test["gap"] > 0
    df_test["actual_over"] = df_test["actual_total"] > df_test["market_total_open"]
    df_test = df_test[df_test["actual_total"] != df_test["market_total_open"]]

    return df_test


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    test_df = full_df[full_df["season"] == 2025]

    for label, start, end in TRAINING_WINDOWS:
        train_df = full_df[(full_df["season"] >= start) & (full_df["season"] <= end)]
        df_result = evaluate(train_df, test_df)

        print(f"\n=== {label} -> tested on 2025 ({len(train_df)} training games) ===")
        for threshold in GAP_THRESHOLDS:
            confident = df_result[df_result["gap"].abs() >= threshold]
            if len(confident) == 0:
                print(f"  Gap>={threshold}: no bets")
                continue
            correct = confident["bet_over"] == confident["actual_over"]
            win_rate = correct.mean() * 100
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {len(confident)} bets, {win_rate:.1f}%{marker}")


if __name__ == "__main__":
    run()