"""
Systematic category search for Total - mirrors the approach that
actually found Candidate A for Spread, never yet applied to Total.
Tests every combination of feature categories (sized 1-5) against
Phase 1 only (train 2021-2023/validate 2024), 100-bet minimum floor
(learned from Spread's early mistake letting tiny samples dominate).
"""
import itertools
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

TRAIN_START, TRAIN_END, VALIDATE_YEAR = 2021, 2023, 2024
GAP_THRESHOLD = 5
MIN_BETS_REQUIRED = 100
MAX_CATEGORY_SIZE = 5

CATEGORIES = {
    "combined_efficiency": ["combined_off_success_rate", "combined_off_explosiveness",
                             "combined_off_ppa", "combined_def_ppa"],
    "combined_points_per_opp": ["combined_off_points_per_opp", "combined_def_points_per_opp"],
    "combined_pace": ["combined_pace"],
    "combined_third_down": ["combined_off_third_down_pct", "combined_def_third_down_pct_allowed"],
    "combined_turnover": ["combined_turnover_margin_abs_gap"],
    "combined_field_position": ["combined_field_position_predicted_points"],
    "matchup_scoring": ["combined_matchup_scoring_potential", "home_matchup_scoring_potential",
                         "away_matchup_scoring_potential"],
    "matchup_trenches": ["combined_trenches_potential"],
    "weather": ["temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate"],
    "dome": ["is_dome"],
}


def build_derived_columns(df):
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
    df["combined_off_success_rate"] = df["home_off_success_rate"] + df["away_off_success_rate"]
    df["combined_off_explosiveness"] = df["home_off_explosiveness"] + df["away_off_explosiveness"]
    df["combined_off_ppa"] = df["home_off_ppa"] + df["away_off_ppa"]
    df["combined_def_ppa"] = df["home_def_ppa"] + df["away_def_ppa"]
    df["combined_def_points_per_opp"] = df["home_def_points_per_opportunity"] + df["away_def_points_per_opportunity"]
    df["combined_off_points_per_opp"] = df["home_off_points_per_opportunity"] + df["away_off_points_per_opportunity"]
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]
    df["combined_off_third_down_pct"] = df["home_off_third_down_pct"] + df["away_off_third_down_pct"]
    df["combined_def_third_down_pct_allowed"] = df["home_def_third_down_pct_allowed"] + df["away_def_third_down_pct_allowed"]
    df["combined_turnover_margin_abs_gap"] = (df["home_turnover_margin"] - df["away_turnover_margin"]).abs()
    df["combined_field_position_predicted_points"] = (
        df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"]
    )
    df["home_matchup_scoring_potential"] = df["matchup_home_pass_off_vs_away_pass_def"] + df["matchup_home_rush_off_vs_away_rush_def"]
    df["away_matchup_scoring_potential"] = df["matchup_away_pass_off_vs_home_pass_def"] + df["matchup_away_rush_off_vs_home_rush_def"]
    df["combined_matchup_scoring_potential"] = df["home_matchup_scoring_potential"] + df["away_matchup_scoring_potential"]
    df["combined_trenches_potential"] = (
        df["matchup_home_run_block_vs_away_run_stop"] + df["matchup_away_run_block_vs_home_run_stop"] +
        df["matchup_home_power_vs_away_stuff"] + df["matchup_away_power_vs_home_stuff"]
    )
    return df


def evaluate(df_train, df_val, categories):
    feature_cols = []
    for cat in categories:
        feature_cols.extend(CATEGORIES[cat])

    X_train, y_train = df_train[feature_cols], df_train["actual_total"]
    X_val, y_val = df_val[feature_cols], df_val["actual_total"]

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train)
    preds = model.predict(X_val_scaled)

    gap = preds - df_val["market_total_open"].values
    bet_over = gap > 0
    actual_over = (df_val["actual_total"] > df_val["market_total_open"]).values

    confident = np.abs(gap) >= GAP_THRESHOLD
    if confident.sum() < MIN_BETS_REQUIRED:
        return None

    correct = bet_over[confident] == actual_over[confident]
    win_rate = correct.mean() * 100
    return win_rate, confident.sum()


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= VALIDATE_YEAR].copy()
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df = build_derived_columns(full_df)

    train_df = full_df[(full_df["season"] >= TRAIN_START) & (full_df["season"] <= TRAIN_END)]
    val_df = full_df[full_df["season"] == VALIDATE_YEAR]

    category_names = list(CATEGORIES.keys())
    results = []

    for size in range(1, MAX_CATEGORY_SIZE + 1):
        for combo in itertools.combinations(category_names, size):
            result = evaluate(train_df, val_df, combo)
            if result is None:
                continue
            win_rate, n_bets = result
            results.append((combo, win_rate, n_bets))

    results.sort(key=lambda x: -x[1])

    print(f"Tested {len(results)} valid combinations (Gap>={GAP_THRESHOLD}, min {MIN_BETS_REQUIRED} bets)\n")
    print("=== TOP 20 ===")
    for combo, win_rate, n_bets in results[:20]:
        marker = " <-- above breakeven" if win_rate >= 52.4 else ""
        print(f"  {win_rate:.1f}% ({n_bets} bets): {', '.join(combo)}{marker}")


if __name__ == "__main__":
    run()