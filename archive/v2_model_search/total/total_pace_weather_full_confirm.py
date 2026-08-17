"""
Phase 2 confirmation for the pace+weather Total candidate - the
strongest, simplest, most consistently-recurring result from the
category search, confirmed on two independent Phase 1 splits. Full
4-fold walk-forward (spends a real look at 2025) + bootstrap, same
standard as every approved Spread system.
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

GAP_THRESHOLDS = [3, 5, 7]
BREAKEVEN = 0.524
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]
N_BOOTSTRAP = 10000


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]

    feature_cols = ["combined_pace", "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome"]
    return df, df[feature_cols], df["actual_total"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    results_by_threshold = {t: {"wins": 0, "total": 0, "correct_arr": []} for t in GAP_THRESHOLDS}

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
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

        print(f"\n=== {test_year} ===")
        for threshold in GAP_THRESHOLDS:
            confident = df_test[df_test["gap"].abs() >= threshold]
            if len(confident) == 0:
                print(f"  Gap>={threshold}: no bets")
                continue
            correct = (confident["bet_over"] == confident["actual_over"])
            wins = int(correct.sum())
            total = len(correct)
            win_rate = wins / total * 100
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {wins}/{total} = {win_rate:.1f}%{marker}")

            results_by_threshold[threshold]["wins"] += wins
            results_by_threshold[threshold]["total"] += total
            results_by_threshold[threshold]["correct_arr"].extend(correct.astype(int).tolist())

    print("\n\n" + "="*70)
    print("POOLED RESULTS + BOOTSTRAP, BY THRESHOLD")
    print("="*70)

    rng = np.random.default_rng(42)
    for threshold in GAP_THRESHOLDS:
        wins = results_by_threshold[threshold]["wins"]
        total = results_by_threshold[threshold]["total"]
        if total == 0:
            continue
        pooled_rate = wins / total * 100
        pvalue = binomtest(wins, total, p=BREAKEVEN, alternative="greater").pvalue

        correct_arr = np.array(results_by_threshold[threshold]["correct_arr"])
        bootstrap_rates = np.array([
            rng.choice(correct_arr, size=len(correct_arr), replace=True).mean() * 100
            for _ in range(N_BOOTSTRAP)
        ])
        pct_profitable = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
        ci_low, ci_high = np.percentile(bootstrap_rates, [2.5, 97.5])

        print(f"\nGap >= {threshold}: {wins}/{total} = {pooled_rate:.1f}% | p={pvalue:.4f}")
        print(f"  Bootstrap: {pct_profitable:.1f}% of resamples profitable, 95% CI [{ci_low:.1f}%, {ci_high:.1f}%]")


if __name__ == "__main__":
    run()