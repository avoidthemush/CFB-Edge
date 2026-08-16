"""
Real test of the recency-drift hypothesis, properly separated: three
SAFE folds (2021->2022, 2022->2023, 2023->2024) that never touch 2025 at
all, checked FIRST. The 2025 fold only gets examined if the safe folds
already support the hypothesis - avoids spending yet another look at
2025 on an idea that hasn't earned it yet.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

GAP_THRESHOLDS = [3, 5, 7]

SAFE_FOLDS = [
    (2021, 2022),
    (2022, 2023),
    (2023, 2024),
]
SPEND_FOLD = (2024, 2025)  # only look at this if the safe folds justify it


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]

    feature_cols = ["combined_pace", "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome"]
    return df, df[feature_cols], df["actual_total"], feature_cols


def evaluate_fold(full_df, train_year, test_year):
    train_df = full_df[full_df["season"] == train_year]
    test_df = full_df[full_df["season"] == test_year]

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

    results = {}
    for threshold in GAP_THRESHOLDS:
        confident = df_test[df_test["gap"].abs() >= threshold]
        if len(confident) == 0:
            results[threshold] = None
            continue
        correct = confident["bet_over"] == confident["actual_over"]
        results[threshold] = (correct.mean() * 100, len(confident))
    return results


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")

    print("=== SAFE FOLDS ONLY (2025 never touched) ===")
    safe_pass_count = 0
    safe_total_checks = 0
    for train_year, test_year in SAFE_FOLDS:
        results = evaluate_fold(full_df, train_year, test_year)
        print(f"\nTrain {train_year} -> Test {test_year}:")
        for threshold, r in results.items():
            if r is None:
                print(f"  Gap>={threshold}: no bets")
                continue
            win_rate, n = r
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {n} bets, {win_rate:.1f}%{marker}")
            safe_total_checks += 1
            if win_rate >= 52.4:
                safe_pass_count += 1

    print(f"\n{'='*70}")
    print(f"SAFE FOLDS SUMMARY: {safe_pass_count}/{safe_total_checks} threshold-checks cleared breakeven")
    print(f"{'='*70}")

    if safe_pass_count >= safe_total_checks * 0.6:
        print("\nSafe folds are reasonably supportive - proceeding to check the 2025 fold.")
        full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
        full_df_with_2025 = pd.concat([full_df, full_df_2025], ignore_index=True)
        train_year, test_year = SPEND_FOLD
        results = evaluate_fold(full_df_with_2025, train_year, test_year)
        print(f"\nTrain {train_year} -> Test {test_year} (2025 - SPENDING a real look):")
        for threshold, r in results.items():
            if r is None:
                print(f"  Gap>={threshold}: no bets")
                continue
            win_rate, n = r
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {n} bets, {win_rate:.1f}%{marker}")
    else:
        print("\nSafe folds do NOT sufficiently support the hypothesis - "
              "NOT spending a look at 2025. Recency-window idea likely not real.")


if __name__ == "__main__":
    run()