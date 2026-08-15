"""
Re-tests weeks 1-4 specifically, now WITH returning QB and coach
upgrade/downgrade score included - the features built to directly
address the "returning production, refined coach comparison" gap
identified in ats_early_season_analysis.py. Compares calibration
(not just win rate) against the original weeks 1-4 result, and against
the Week 5+ locked baseline as a reference for what "working" looks like.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
MARKET_COLUMNS = [
    "market_spread", "market_spread_open", "market_total", "market_total_open",
    "market_home_moneyline", "market_away_moneyline",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]
RECRUITING_COLS = [
    "home_recruiting_rank", "away_recruiting_rank", "diff_recruiting_rank",
    "home_recruiting_points", "away_recruiting_points", "diff_recruiting_points",
    "home_off_new_talent_impact", "away_off_new_talent_impact", "diff_off_new_talent_impact",
    "home_def_new_talent_impact", "away_def_new_talent_impact", "diff_def_new_talent_impact",
    "talent_edge_early_season", "recruiting_edge_early_season",
]

CALIBRATION_BUCKETS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def prepare(df, exclude_cols):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    base_exclude = NON_FEATURE_COLUMNS + MARKET_COLUMNS + ID_COLUMNS + exclude_cols + \
                   ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in df.columns if c not in base_exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    # Only exclude recruiting - KEEP returning QB and coach upgrade score
    # this time, unlike the locked-baseline check above
    exclude = [c for c in RECRUITING_COLS if c in full_df.columns]

    all_preds = []
    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude)
        df_test, X_test, y_test, _ = prepare(test_df, exclude)

        if len(df_train) < 100 or len(df_test) < 30:
            continue

        imputer = SimpleImputer(strategy="median")
        X_train_imputed = imputer.fit_transform(X_train)
        X_test_imputed = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imputed)
        X_test_scaled = scaler.transform(X_test_imputed)

        model = LogisticRegression(max_iter=2000, C=0.1, random_state=42)
        model.fit(X_train_scaled, y_train)
        probs = model.predict_proba(X_test_scaled)[:, 1]

        result = df_test.copy()
        result["prob"] = probs
        result["bet_on_home"] = probs >= 0.5
        result["confidence"] = result["prob"].where(result["bet_on_home"], 1 - result["prob"])
        result["actual_home_covers"] = y_test.values.astype(bool)
        result["correct"] = result["bet_on_home"] == result["actual_home_covers"]
        all_preds.append(result)

    preds = pd.concat(all_preds, ignore_index=True)

    print("=== WEEKS 1-4, WITH returning QB + coach upgrade score - calibration ===")
    early = preds[preds["week"] <= 4]
    print(f"{'Stated confidence':<20}{'# predictions':>15}{'Actual accuracy':>18}")
    for low, high in CALIBRATION_BUCKETS:
        bucket = early[(early["confidence"] >= low) & (early["confidence"] < high)]
        if len(bucket) == 0:
            print(f"{low:.2f}-{high:.2f}{'':>15}no predictions")
            continue
        actual_acc = bucket["correct"].mean() * 100
        print(f"{low:.2f}-{high:.2f}{'':>7}{len(bucket):>15}{actual_acc:>17.1f}%")

    print(f"\nPlain accuracy, ALL weeks 1-4 games: {early['correct'].mean()*100:.1f}% "
          f"(previous result without these features: 48.5%)")

    print("\n\n=== Reference: WEEKS 5+, same feature set (sanity comparison) ===")
    late = preds[preds["week"] > 4]
    for low, high in CALIBRATION_BUCKETS:
        bucket = late[(late["confidence"] >= low) & (late["confidence"] < high)]
        if len(bucket) == 0:
            continue
        actual_acc = bucket["correct"].mean() * 100
        print(f"{low:.2f}-{high:.2f}{'':>7}{len(bucket):>15}{actual_acc:>17.1f}%")


if __name__ == "__main__":
    run()