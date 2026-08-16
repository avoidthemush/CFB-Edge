"""
Works through the TOP CANDIDATES from the category search as a real
checklist, not just the single top result - rechecking each on an
independent internal split before any of them earn a Phase 2 test.
Picks a spread of distinct combinations from the top 20, not just the
first one.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

GAP_THRESHOLDS = [3, 5, 7]

SPLITS = [
    ("train 2021-2023, validate 2024", 2021, 2023, 2024),
    ("train 2021-2022, validate 2023", 2021, 2022, 2023),
]

CATEGORY_COLS = {
    "combined_pace": ["combined_pace"],
    "weather": ["temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate"],
    "matchup_scoring": ["combined_matchup_scoring_potential", "home_matchup_scoring_potential",
                         "away_matchup_scoring_potential"],
    "combined_third_down": ["combined_off_third_down_pct", "combined_def_third_down_pct_allowed"],
    "combined_turnover": ["combined_turnover_margin_abs_gap"],
    "matchup_trenches": ["combined_trenches_potential"],
    "combined_field_position": ["combined_field_position_predicted_points"],
    "dome": ["is_dome"],
}

# Chosen from the top 20 to cover a real spread - not just #1
CANDIDATES = {
    "#1: pace + weather": ["combined_pace", "weather"],
    "#2: pace + matchup_scoring + weather": ["combined_pace", "matchup_scoring", "weather"],
    "#6: third_down + turnover + trenches + dome": ["combined_third_down", "combined_turnover", "matchup_trenches", "dome"],
    "#8: third_down + matchup_scoring": ["combined_third_down", "matchup_scoring"],
    "#10: field_position + trenches + third_down": ["combined_third_down", "combined_field_position", "matchup_trenches"],
    "#14: pace + third_down + turnover": ["combined_pace", "combined_third_down", "combined_turnover"],
}


def build_derived_columns(df):
    df = df.copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})
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


def evaluate(full_df, categories, train_start, train_end, val_year):
    feature_cols = []
    for cat in categories:
        feature_cols.extend(CATEGORY_COLS[cat])

    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    val_df = full_df[full_df["season"] == val_year]

    X_train, y_train = train_df[feature_cols], train_df["actual_total"]
    X_val, y_val = val_df[feature_cols], val_df["actual_total"]

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train)
    preds = model.predict(X_val_scaled)

    gap = preds - val_df["market_total_open"].values
    bet_over = gap > 0
    actual_over = (val_df["actual_total"] > val_df["market_total_open"]).values
    valid = val_df["actual_total"].values != val_df["market_total_open"].values

    results = {}
    for threshold in GAP_THRESHOLDS:
        confident = (np.abs(gap) >= threshold) & valid
        if confident.sum() == 0:
            results[threshold] = None
            continue
        correct = bet_over[confident] == actual_over[confident]
        results[threshold] = (correct.mean() * 100, confident.sum())

    return results


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]
    full_df = build_derived_columns(full_df)

    summary = {}

    for label, categories in CANDIDATES.items():
        print(f"\n{'='*70}")
        print(f"{label}: {categories}")
        print(f"{'='*70}")

        split_results = []
        for split_label, start, end, val in SPLITS:
            results = evaluate(full_df, categories, start, end, val)
            print(f"  {split_label}:")
            for threshold, r in results.items():
                if r is None:
                    print(f"    Gap>={threshold}: no bets")
                else:
                    win_rate, n = r
                    marker = " <-- above breakeven" if win_rate >= 52.4 else ""
                    print(f"    Gap>={threshold}: {n} bets, {win_rate:.1f}%{marker}")
            split_results.append(results)

        # Check: does this candidate clear breakeven at Gap>=5 on BOTH splits?
        both_clear = all(
            r[5] is not None and r[5][0] >= 52.4 for r in split_results
        )
        summary[label] = both_clear

    print(f"\n\n{'='*70}")
    print("SUMMARY: candidates clearing breakeven at Gap>=5 on BOTH splits")
    print(f"{'='*70}")
    for label, passed in summary.items():
        print(f"  {'PASS' if passed else 'fail'}: {label}")


if __name__ == "__main__":
    run()