"""
Refines the rolling-window finding with smooth recency weighting instead
of a hard cutoff - a decay-weighted approach keeps ALL available prior
years in training, but recent years count more. Tests several decay
rates against THREE SAFE folds only (test 2022, 2023, 2024) - 2025
deliberately untouched, since we've already spent two real looks at it
tonight (pace+weather, hard rolling-window). Only the winning decay rate
should ever be tested against 2025.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

GAP_THRESHOLDS = [3, 5, 7]
DECAY_RATES = [0.3, 0.5, 0.7, 1.0]  # 1.0 = no decay (equal weight, baseline)

# SAFE folds only - test years that never touch 2025
SAFE_TEST_YEARS = [2022, 2023, 2024]


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
    feature_cols = ["combined_pace", "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome"]
    return df, df[feature_cols], df["actual_total"], feature_cols


def evaluate(full_df, test_year, decay_rate):
    train_df = full_df[full_df["season"] < test_year]
    test_df = full_df[full_df["season"] == test_year]

    if len(train_df) == 0:
        return None

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_test, X_test, y_test, _ = prepare(test_df)

    # Recency weight: most recent prior year = weight 1.0, each year
    # further back multiplied by decay_rate again (exponential decay)
    years_back = test_year - df_train["season"]
    sample_weight = decay_rate ** (years_back - 1)

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train, sample_weight=sample_weight)
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
    full_df = full_df[full_df["season"] <= 2024]  # hard block - 2025 never loaded

    summary = {}

    for decay_rate in DECAY_RATES:
        print(f"\n{'='*70}")
        print(f"Decay rate = {decay_rate} {'(no decay - equal weight baseline)' if decay_rate == 1.0 else ''}")
        print(f"{'='*70}")

        pass_count = 0
        total_checks = 0
        for test_year in SAFE_TEST_YEARS:
            results = evaluate(full_df, test_year, decay_rate)
            if results is None:
                continue
            print(f"  Test {test_year}:")
            for threshold, r in results.items():
                if r is None:
                    print(f"    Gap>={threshold}: no bets")
                    continue
                win_rate, n = r
                marker = " <-- above breakeven" if win_rate >= 52.4 else ""
                print(f"    Gap>={threshold}: {n} bets, {win_rate:.1f}%{marker}")
                total_checks += 1
                if win_rate >= 52.4:
                    pass_count += 1

        summary[decay_rate] = (pass_count, total_checks)

    print(f"\n\n{'='*70}")
    print("SUMMARY: threshold-checks cleared breakeven, by decay rate")
    print(f"{'='*70}")
    for decay_rate, (passed, total) in summary.items():
        print(f"  Decay {decay_rate}: {passed}/{total} cleared breakeven")


if __name__ == "__main__":
    run()