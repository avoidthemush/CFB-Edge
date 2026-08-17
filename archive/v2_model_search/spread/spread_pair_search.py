"""
Standing process, next iteration: tests PAIRS of remaining categories
added to Candidate A's base (not just one at a time), still at the
category level (not individual features - that's the search method we
already proved overfits at our data scale). Train 2021-2023, validate
2024 only - 2025 never touched here.
"""
import itertools
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]

BASE_PATTERNS = {
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "raw_offense_defense_stats": ["off_success_rate", "off_explosiveness", "def_havoc_rate",
                                    "def_points_per_opportunity", "def_success_rate_allowed",
                                    "off_line_yards", "off_power_success", "def_stuff_rate",
                                    "off_ppa", "def_ppa"],
}

ADDITIONAL_CATEGORIES = {
    "ratings": ["sp+_rating", "srs_rating", "fpi_rating", "elo_rating"],
    "recruiting_talent": ["recruiting_rank", "recruiting_points", "new_talent_impact",
                           "talent_edge_early_season", "recruiting_edge_early_season"],
    "matchups_pass_rush": ["matchup_home_pass_off", "matchup_away_pass_off",
                            "matchup_home_rush_off", "matchup_away_rush_off"],
    "matchups_trenches": ["matchup_home_run_block", "matchup_away_run_block",
                           "matchup_home_power", "matchup_away_power", "net_matchup_advantage"],
    "coach_quality": ["coach_career_win_pct", "coach_career_avg_sp", "coach_experience_seasons",
                       "coach_upgrade_score"],
    "coach_h2h": ["coach_h2h"],
    "weather": ["temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate"],
}

TRAIN_START, TRAIN_END, VALIDATE_YEAR = 2021, 2023, 2024
CONFIDENCE_THRESHOLD = 0.60


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

    keep = set(["neutral_site", "is_dome"])
    for patterns in patterns_list:
        keep.update(get_cols_for_patterns(all_columns, patterns))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def evaluate(full_df, all_columns, patterns_list):
    if full_df["season"].max() >= 2025:
        raise ValueError("Blocked: 2025 present")

    train_df = full_df[(full_df["season"] >= TRAIN_START) & (full_df["season"] <= TRAIN_END)]
    val_df = full_df[full_df["season"] == VALIDATE_YEAR]

    df_train, X_train, y_train, feature_cols = prepare(train_df, patterns_list, all_columns)
    df_val, X_val, y_val, _ = prepare(val_df, patterns_list, all_columns)

    if len(df_train) < 100 or len(df_val) < 30:
        return None

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_val_scaled)[:, 1]

    confident_home = probs >= CONFIDENCE_THRESHOLD
    confident_away = probs <= (1 - CONFIDENCE_THRESHOLD)
    bet_mask = confident_home | confident_away
    if bet_mask.sum() < 15:
        return None

    predicted_home_covers = confident_home[bet_mask]
    actual_home_covers = y_val.values[bet_mask]
    correct = predicted_home_covers == actual_home_covers.astype(bool)
    return correct.mean() * 100, bet_mask.sum()


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= VALIDATE_YEAR]
    all_columns = full_df.columns.tolist()

    base_patterns = list(BASE_PATTERNS.values())
    baseline_score, baseline_n = evaluate(full_df, all_columns, base_patterns)
    print(f"BASELINE (Candidate A): {baseline_score:.2f}% ({baseline_n} bets)\n")

    results = []
    category_names = list(ADDITIONAL_CATEGORIES.keys())

    for cat1, cat2 in itertools.combinations(category_names, 2):
        test_patterns = base_patterns + [ADDITIONAL_CATEGORIES[cat1], ADDITIONAL_CATEGORIES[cat2]]
        result = evaluate(full_df, all_columns, test_patterns)
        if result is None:
            continue
        score, n = result
        results.append((f"{cat1} + {cat2}", score, n))

    results.sort(key=lambda x: -x[1])

    print("=== All pairs, sorted by validation win rate ===")
    for label, score, n in results:
        marker = " *** BEATS BASELINE" if score > baseline_score else ""
        print(f"  {score:.2f}% ({n} bets): {label}{marker}")

    beating_baseline = [r for r in results if r[1] > baseline_score]
    print(f"\n{len(beating_baseline)} of {len(results)} pairs beat the baseline")


if __name__ == "__main__":
    run()