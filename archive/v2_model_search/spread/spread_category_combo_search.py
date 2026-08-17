"""
Systematic search across EVERY combination of feature categories (2^n),
not just a handful of hand-picked ablations. Uses internal split (train
2015-2022, validate 2023) - 2025 untouched during search. Reports the
top configurations by win rate for follow-up confirmation via the
standard 4-fold walk-forward.
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

# Feature categories, grouped by football concept - the combinatorial
# search tests every possible ON/OFF combination of these groups
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

CONFIDENCE_THRESHOLD = 0.60


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

    keep = set(["neutral_site", "is_dome", "market_spread_open"])
    for cat in active_categories:
        keep.update(get_cols_for_category(all_columns, CATEGORY_PATTERNS[cat]))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers", "market_spread_open"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    all_columns = full_df.columns.tolist()

    train_df = full_df[full_df["season"] <= 2022]
    val_df = full_df[full_df["season"] == 2023]

    category_names = list(CATEGORY_PATTERNS.keys())
    print(f"Testing all 2^{len(category_names)} = {2**len(category_names)} category combinations")
    print(f"Train 2015-2022, validate 2023 (internal split, 2025 untouched)\n")

    results = []

    for r in range(1, len(category_names) + 1):
        for combo in itertools.combinations(category_names, r):
            df_train, X_train, y_train, feature_cols = prepare(train_df, combo, all_columns)
            df_val, X_val, y_val, _ = prepare(val_df, combo, all_columns)

            if len(feature_cols) == 0:
                continue

            imputer = SimpleImputer(strategy="median")
            X_train_imp = imputer.fit_transform(X_train)
            X_val_imp = imputer.transform(X_val)
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train_imp)
            X_val_scaled = scaler.transform(X_val_imp)

            model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
            model.fit(X_train_scaled, y_train)
            probs = model.predict_proba(X_val_scaled)[:, 1]

            confident = (probs >= CONFIDENCE_THRESHOLD) | (probs <= (1 - CONFIDENCE_THRESHOLD))
            if confident.sum() < 15:  # skip configs with too few bets to mean anything
                continue

            bet_home = probs[confident] >= CONFIDENCE_THRESHOLD
            actual_home = y_val.values[confident].astype(bool)
            win_rate = (bet_home == actual_home).mean() * 100

            results.append((combo, win_rate, confident.sum()))

    results.sort(key=lambda x: -x[1])

    print(f"Tested {len(results)} valid combinations (skipped ones with <15 bets)\n")
    print("=== TOP 15 combinations by win rate (2023 internal validation) ===")
    for combo, win_rate, n_bets in results[:15]:
        print(f"  {win_rate:.1f}% ({n_bets} bets): {', '.join(combo)}")

    print("\n=== For comparison, current LOCKED config (all categories except recruiting) ===")
    locked_combo = tuple(c for c in category_names if c != "recruiting_talent")
    for combo, win_rate, n_bets in results:
        if set(combo) == set(locked_combo):
            print(f"  {win_rate:.1f}% ({n_bets} bets): {', '.join(combo)}")
            break


if __name__ == "__main__":
    run()