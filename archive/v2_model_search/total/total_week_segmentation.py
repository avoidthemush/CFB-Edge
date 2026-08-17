"""
Genuinely new angle: does Total's signal concentrate in specific weeks,
the way Spread's did (week>=5)? Never checked. Uses the rolling 1-year-
prior training approach (strongest found so far) on the three SAFE test
years only (2022-2024) - 2025 untouched, since we've already spent two
real looks at it tonight.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

GAP_THRESHOLD = 5
SAFE_TEST_YEARS = [2022, 2023, 2024]
WEEK_BUCKETS = [(1, 4, "Weeks 1-4"), (5, 9, "Weeks 5-9"), (10, 15, "Weeks 10-15")]


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
    feature_cols = ["combined_pace", "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome"]
    return df, df[feature_cols], df["actual_total"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    all_bets = []

    for test_year in SAFE_TEST_YEARS:
        train_df = full_df[full_df["season"] == test_year - 1]
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
        df_test = df_test[df_test["gap"].abs() >= GAP_THRESHOLD]
        df_test["won"] = df_test["bet_over"] == df_test["actual_over"]

        all_bets.append(df_test[["week", "won"]])

    bets = pd.concat(all_bets, ignore_index=True)
    print(f"Total bets across 3 safe years (Gap>={GAP_THRESHOLD}): {len(bets)}\n")

    print("=== By week bucket ===")
    for low, high, label in WEEK_BUCKETS:
        bucket = bets[(bets["week"] >= low) & (bets["week"] <= high)]
        if len(bucket) == 0:
            print(f"{label}: no bets")
            continue
        win_rate = bucket["won"].mean() * 100
        marker = " <-- above breakeven" if win_rate >= 52.4 else ""
        print(f"{label}: {len(bucket)} bets, {win_rate:.1f}%{marker}")

    print("\n=== By individual week (where sample allows) ===")
    for week in sorted(bets["week"].unique()):
        week_bets = bets[bets["week"] == week]
        if len(week_bets) < 20:
            continue
        win_rate = week_bets["won"].mean() * 100
        marker = " <-- above breakeven" if win_rate >= 52.4 else ""
        print(f"Week {week}: {len(week_bets)} bets, {win_rate:.1f}%{marker}")


if __name__ == "__main__":
    run()