"""
Confirmatory test for the strongest STRUCTURAL patterns from the 1,024-
combination search (spread_category_combo_search.py) - not just the
single top-ranked result, which is most vulnerable to being the
"luckiest roll" out of that many tries. Runs each candidate through the
REAL 4-fold walk-forward (touches 2025, same standard as every other
validated result tonight) for genuine corroboration, not just an
internal-split repeat.
"""
import pandas as pd
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]

CATEGORY_PATTERNS = {
    "ratings": ["sp+_rating", "srs_rating", "fpi_rating", "elo_rating"],
    "recruiting_talent": ["recruiting_rank", "recruiting_points", "new_talent_impact",
                           "talent_edge_early_season", "recruiting_edge_early_season"],
    "matchups_pass_rush": ["matchup_home_pass_off", "matchup_away_pass_off",
                            "matchup_home_rush_off", "matchup_away_rush_off"],
    "matchups_trenches": ["matchup_home_run_block", "matchup_away_run_block",
                           "matchup_home_power", "matchup_away_power", "net_matchup_advantage"],
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "coach_quality": ["coach_career_win_pct", "coach_career_avg_sp", "coach_experience_seasons",
                       "coach_upgrade_score"],
    "coach_h2h": ["coach_h2h"],
    "weather": ["temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate"],
    "raw_offense_defense_stats": ["off_success_rate", "off_explosiveness", "def_havoc_rate",
                                    "def_points_per_opportunity", "def_success_rate_allowed",
                                    "off_line_yards", "off_power_success", "def_stuff_rate",
                                    "off_ppa", "def_ppa"],
}

# Candidates chosen for STRUCTURAL reasons (recurring pattern across many
# top-15 results), not just picking #1 by raw number
CANDIDATES = {
    "A: minimal top combo (QB+RP+raw stats)": ["returning_qb", "returning_production", "raw_offense_defense_stats"],
    "B: simplest recurring pair (RP+raw stats)": ["returning_production", "raw_offense_defense_stats"],
    "C: matchups+RP+H2H+raw stats": ["matchups_pass_rush", "returning_production", "coach_h2h", "raw_offense_defense_stats"],
    "D: CURRENT LOCKED (everything except recruiting)": [c for c in CATEGORY_PATTERNS if c != "recruiting_talent"],
}

CONFIDENCE_THRESHOLD = 0.60
BREAKEVEN = 0.524
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def get_cols_for_category(all_columns, patterns):
    return [c for c in all_columns if any(p in c for p in patterns)]


def prepare(df, active_categories, all_columns):
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
    for cat in active_categories:
        keep.update(get_cols_for_category(all_columns, CATEGORY_PATTERNS[cat]))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    all_columns = full_df.columns.tolist()

    for label, categories in CANDIDATES.items():
        print(f"\n{'='*70}")
        print(f"{label}")
        print(f"Categories: {', '.join(categories)}")
        print(f"{'='*70}")

        pooled_wins = 0
        pooled_total = 0
        year_rates = []

        for train_start, train_end, test_year in FOLDS:
            train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
            test_df = full_df[full_df["season"] == test_year]

            df_train, X_train, y_train, feature_cols = prepare(train_df, categories, all_columns)
            df_test, X_test, y_test, _ = prepare(test_df, categories, all_columns)

            if len(df_train) < 100 or len(df_test) < 30 or len(feature_cols) == 0:
                continue

            imputer = SimpleImputer(strategy="median")
            X_train_imp = imputer.fit_transform(X_train)
            X_test_imp = imputer.transform(X_test)
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train_imp)
            X_test_scaled = scaler.transform(X_test_imp)

            model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
            model.fit(X_train_scaled, y_train)
            probs = model.predict_proba(X_test_scaled)[:, 1]

            confident_home = probs >= CONFIDENCE_THRESHOLD
            confident_away = probs <= (1 - CONFIDENCE_THRESHOLD)
            bet_mask = confident_home | confident_away

            if bet_mask.sum() == 0:
                continue

            predicted_home_covers = confident_home[bet_mask]
            actual_home_covers = y_test.values[bet_mask]
            correct = predicted_home_covers == actual_home_covers.astype(bool)
            wins = int(correct.sum())
            total = len(correct)
            win_rate = wins / total * 100

            pooled_wins += wins
            pooled_total += total
            year_rates.append((test_year, win_rate, total))

            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  {test_year}: {wins}/{total} = {win_rate:.1f}%{marker}")

        above = sum(1 for _, r, _ in year_rates if r >= 52.4)
        if pooled_total > 0:
            vs_breakeven = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater")
            print(f"\n  POOLED: {pooled_wins}/{pooled_total} = {pooled_wins/pooled_total*100:.1f}% "
                  f"| {above}/{len(year_rates)} years above breakeven | vs 52.4%: p={vs_breakeven.pvalue:.4f}")


if __name__ == "__main__":
    run()