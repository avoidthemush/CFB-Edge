"""
Tests two research-grounded angles using Candidate A's EXISTING trained
predictions (no new model, no new data pull):
1. Coach experience gap as a standalone rule (independent of Candidate
   A's confidence threshold - does experience gap alone predict covers?)
2. Large ("double-digit") underdog segment specifically, using Candidate
   A's existing confidence>=0.60 predictions, split by spread size.
"""
import pandas as pd
import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]

CANDIDATE_A_PATTERNS = {
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "raw_offense_defense_stats": ["off_success_rate", "off_explosiveness", "def_havoc_rate",
                                    "def_points_per_opportunity", "def_success_rate_allowed",
                                    "off_line_yards", "off_power_success", "def_stuff_rate",
                                    "off_ppa", "def_ppa"],
}

CONFIDENCE_THRESHOLD = 0.60
BREAKEVEN = 0.524
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def get_cols_for_patterns(all_columns, patterns):
    return [c for c in all_columns if any(p in c for p in patterns)]


def prepare(df, patterns_list, all_columns):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    keep = set(["neutral_site", "is_dome", "diff_coach_experience_seasons"])
    for patterns in patterns_list:
        keep.update(get_cols_for_patterns(all_columns, patterns))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def get_predictions_for_fold(full_df, all_columns, patterns_list, train_start, train_end, test_year):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    test_df = full_df[full_df["season"] == test_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df, patterns_list, all_columns)
    df_test, X_test, y_test, _ = prepare(test_df, patterns_list, all_columns)

    if len(df_train) < 100 or len(df_test) < 30:
        return None

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_test_scaled)[:, 1]

    df_test = df_test.copy()
    df_test["prob_home_covers"] = probs
    df_test["actual_home_covers"] = y_test.values.astype(bool)
    return df_test


def test_1_coach_experience_gap(full_df, all_columns):
    print("=== TEST 1: Coach experience gap as a STANDALONE rule (not model-based) ===")
    print("Does the more-experienced coach cover more often, independent of any model?\n")

    for min_gap in [3, 5, 8]:
        wins = 0
        total = 0
        for train_start, train_end, test_year in FOLDS:
            test_df = full_df[full_df["season"] == test_year].copy()
            test_df = test_df[test_df["market_spread_open"].notna() & test_df["actual_spread"].notna()]
            test_df["open_implied_margin"] = -test_df["market_spread_open"]
            test_df["margin_vs_open"] = test_df["actual_spread"] - test_df["open_implied_margin"]
            test_df = test_df[test_df["margin_vs_open"] != 0]

            gap = test_df["diff_coach_experience_seasons"]
            home_more_experienced = gap >= min_gap
            away_more_experienced = gap <= -min_gap
            qualifying = test_df[home_more_experienced | away_more_experienced]

            if len(qualifying) == 0:
                continue

            predicted_experienced_covers = (qualifying["diff_coach_experience_seasons"] >= min_gap)
            actual_home_covers = qualifying["margin_vs_open"] > 0
            correct = predicted_experienced_covers == actual_home_covers
            wins += correct.sum()
            total += len(correct)

        if total > 0:
            rate = wins / total * 100
            marker = " <-- above breakeven" if rate >= 52.4 else ""
            print(f"  Experience gap >= {min_gap} years: {wins}/{total} = {rate:.1f}%{marker}")
        else:
            print(f"  Experience gap >= {min_gap} years: no qualifying games")
    print()


def test_2_large_underdog_segment(full_df, all_columns):
    print("=== TEST 2: Large ('double-digit') underdog segment, using Candidate A's predictions ===\n")

    patterns_list = list(CANDIDATE_A_PATTERNS.values())
    thresholds = [(0, 7, "Small dogs (0-7)"), (7, 14, "Medium dogs (7-14)"), (14, 100, "Large dogs (14+)")]

    for low, high, label in thresholds:
        pooled_wins = 0
        pooled_total = 0
        for train_start, train_end, test_year in FOLDS:
            df_test = get_predictions_for_fold(full_df, all_columns, patterns_list, train_start, train_end, test_year)
            if df_test is None:
                continue

            bet_on_home = df_test["prob_home_covers"] >= 0.5
            confidence = np.where(bet_on_home, df_test["prob_home_covers"], 1 - df_test["prob_home_covers"])
            confident_mask = confidence >= CONFIDENCE_THRESHOLD

            is_underdog_bet = (
                (bet_on_home & (df_test["market_spread_open"] > 0)) |
                (~bet_on_home & (df_test["market_spread_open"] < 0))
            )

            spread_size = df_test["market_spread_open"].abs()
            size_mask = (spread_size >= low) & (spread_size < high)

            final_mask = confident_mask & is_underdog_bet & size_mask
            if final_mask.sum() == 0:
                continue

            predicted = bet_on_home[final_mask]
            actual = df_test["actual_home_covers"][final_mask]
            correct = predicted == actual
            pooled_wins += correct.sum()
            pooled_total += len(correct)

        if pooled_total > 0:
            rate = pooled_wins / pooled_total * 100
            marker = " <-- above breakeven" if rate >= 52.4 else ""
            print(f"  {label}: {pooled_wins}/{pooled_total} = {rate:.1f}%{marker}")
        else:
            print(f"  {label}: no qualifying bets")
    print()


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    all_columns = full_df.columns.tolist()

    test_1_coach_experience_gap(full_df, all_columns)
    test_2_large_underdog_segment(full_df, all_columns)


if __name__ == "__main__":
    run()