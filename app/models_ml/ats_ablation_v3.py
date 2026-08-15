"""
Tests the specific open questions from the restructured (v3) feature
set: does recruiting/talent-impact actually help; do the rush/trenches
matchup features (which didn't rank in the top 20) pull their weight;
does a minimal set (just the two pass-matchups that DID rank) match or
beat the full set. Same walk-forward folds, same fixed threshold
(confidence>=0.6, where the full set showed its clearest pattern) for a
fair, direct comparison across configurations.
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

CONFIDENCE_THRESHOLD = 0.60
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]

RECRUITING_COLS = [
    "home_recruiting_rank", "away_recruiting_rank", "diff_recruiting_rank",
    "home_recruiting_points", "away_recruiting_points", "diff_recruiting_points",
    "home_off_new_talent_impact", "away_off_new_talent_impact", "diff_off_new_talent_impact",
    "home_def_new_talent_impact", "away_def_new_talent_impact", "diff_def_new_talent_impact",
    "talent_edge_early_season", "recruiting_edge_early_season",
]

RUSH_TRENCHES_COLS = [
    "matchup_home_rush_off_vs_away_rush_def", "matchup_away_rush_off_vs_home_rush_def",
    "matchup_home_run_block_vs_away_run_stop", "matchup_away_run_block_vs_home_run_stop",
    "matchup_home_power_vs_away_stuff", "matchup_away_power_vs_home_stuff",
]

PASS_MATCHUP_COLS = [
    "matchup_home_pass_off_vs_away_pass_def", "matchup_away_pass_off_vs_home_pass_def",
]


def prepare(df, exclude_cols=None):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    base_exclude = NON_FEATURE_COLUMNS + MARKET_COLUMNS + ID_COLUMNS + \
                   ["open_implied_margin", "margin_vs_open", "home_covers"]
    if exclude_cols:
        base_exclude = base_exclude + exclude_cols

    feature_cols = [c for c in df.columns if c not in base_exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run_config(full_df, exclude_cols, label):
    fold_results = []

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude_cols)
        df_test, X_test, y_test, _ = prepare(test_df, exclude_cols)

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
        fold_results.append((test_year, win_rate, total))

    avg = sum(r for _, r, _ in fold_results) / len(fold_results) if fold_results else 0
    above = sum(1 for _, r, _ in fold_results if r >= 52.4)

    print(f"\n=== {label} ===")
    for year, rate, n in fold_results:
        marker = " <-- above breakeven" if rate >= 52.4 else ""
        print(f"    {year}: {rate:.1f}% (n={n}){marker}")
    print(f"    AVG: {avg:.1f}% | {above}/{len(fold_results)} years above breakeven")

    return avg, above


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_columns = full_df.columns.tolist()
    everything_except_full = None

    configs = [
        ("FULL SET (baseline)", None),
        ("WITHOUT recruiting/talent-impact", [c for c in RECRUITING_COLS if c in all_columns]),
        ("WITHOUT rush/trenches matchups", [c for c in RUSH_TRENCHES_COLS if c in all_columns]),
        ("WITHOUT both recruiting AND rush/trenches", [c for c in RECRUITING_COLS + RUSH_TRENCHES_COLS if c in all_columns]),
    ]

    results = []
    for label, exclude in configs:
        avg, above = run_config(full_df, exclude, label)
        results.append((label, avg, above))

    # Minimal set: ONLY the two pass-matchup features + core ratings/coach
    # (the features that actually ranked) - a genuinely different test,
    # not just subtraction from the full set
    all_feature_cols_full = prepare(full_df)[3]
    minimal_keep = set(PASS_MATCHUP_COLS + [
        "home_sp+_rating", "away_sp+_rating", "diff_sp+_rating",
        "home_elo_rating", "away_elo_rating", "diff_elo_rating",
        "home_coach_career_avg_sp", "away_coach_career_avg_sp", "diff_coach_career_avg_sp",
        "diff_def_returning_havoc_pct", "home_def_returning_havoc_pct", "away_def_returning_havoc_pct",
        "home_off_ppa", "away_off_ppa", "home_def_ppa", "away_def_ppa",
    ])
    minimal_exclude = [c for c in all_feature_cols_full if c not in minimal_keep]
    avg, above = run_config(full_df, minimal_exclude, "MINIMAL SET (only top-ranked features)")
    results.append(("MINIMAL SET (only top-ranked features)", avg, above))

    print("\n\n=== FINAL COMPARISON ===")
    print(f"{'Config':<45} {'Avg win rate':>14} {'Years above breakeven':>24}")
    for label, avg, above in results:
        print(f"{label:<45} {avg:>13.1f}% {above:>20}/4")


if __name__ == "__main__":
    run()