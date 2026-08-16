"""
Category-based ablation: removes whole GROUPS of related features one
group at a time and re-runs the walk-forward test, to see which
categories genuinely help vs. hurt vs. do nothing - a more meaningful
test than an importance-ranked cutoff, since it respects that features
often only matter in combination with related ones.
"""
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
MARKET_COLUMNS = [
    "market_spread", "market_spread_open", "market_total", "market_total_open",
    "market_home_moneyline", "market_away_moneyline",
]

PARAMS = dict(
    n_estimators=200, max_depth=3, learning_rate=0.02,
    subsample=0.7, colsample_bytree=0.6,
    reg_alpha=0.5, reg_lambda=2.0, min_child_weight=5,
)

VIG_PRICE = -110
CONFIDENCE_THRESHOLD = 0.58  # fixed at a reasonable middle ground for this comparison

FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]

FEATURE_CATEGORIES = {
    "ratings (SP+/SRS/FPI/Elo)": ["sp+_rating", "srs_rating", "fpi_rating", "elo_rating"],
    "efficiency/success-rate": ["off_success_rate", "off_success_rate_pass", "off_success_rate_rush",
                                 "off_explosiveness", "def_havoc_rate", "def_points_per_opportunity",
                                 "off_ppa", "def_ppa", "pass_rate"],
    "talent/recruiting": ["talent_score", "recruiting_points"],
    "returning production": ["off_returning_ppa_pct", "def_returning_havoc_pct"],
    "weather": ["temp_f", "wind_mph", "precip_prob"],
    "context flags": ["neutral_site", "is_dome", "home_is_new_coach_year", "away_is_new_coach_year"],
}


def get_columns_for_category(all_columns, base_names):
    matched = []
    for col in all_columns:
        for base in base_names:
            if col == base or col.startswith(f"home_{base}") or col.startswith(f"away_{base}") or col.startswith(f"diff_{base}"):
                matched.append(col)
    return matched


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

    base_exclude = NON_FEATURE_COLUMNS + MARKET_COLUMNS + ["open_implied_margin", "margin_vs_open", "home_covers"]
    if exclude_cols:
        base_exclude = base_exclude + exclude_cols
    feature_cols = [c for c in df.columns if c not in base_exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    return 100 / abs(vig_price)


def run_config(full_df, exclude_cols, label):
    fold_win_rates = []

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude_cols)
        df_test, X_test, y_test, _ = prepare(test_df, exclude_cols)

        if len(df_train) < 100 or len(df_test) < 30:
            continue

        model = xgb.XGBClassifier(random_state=42, eval_metric="logloss", **PARAMS)
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, 1]

        confident_home = probs >= CONFIDENCE_THRESHOLD
        confident_away = probs <= (1 - CONFIDENCE_THRESHOLD)
        bet_mask = confident_home | confident_away

        if bet_mask.sum() == 0:
            continue

        predicted_home_covers = confident_home[bet_mask]
        actual_home_covers = y_test.values[bet_mask]
        correct = predicted_home_covers == actual_home_covers.astype(bool)
        win_rate = correct.sum() / len(correct) * 100
        fold_win_rates.append((test_year, win_rate, bet_mask.sum()))

    avg = sum(r for _, r, _ in fold_win_rates) / len(fold_win_rates) if fold_win_rates else 0
    above = sum(1 for _, r, _ in fold_win_rates if r >= 52.4)

    print(f"\n=== {label} ===")
    print(f"  Features excluded: {len(exclude_cols) if exclude_cols else 0}")
    for year, rate, n in fold_win_rates:
        marker = " <-- above breakeven" if rate >= 52.4 else ""
        print(f"    {year}: {rate:.1f}% (n={n}){marker}")
    print(f"    AVG: {avg:.1f}% | {above}/{len(fold_win_rates)} years above breakeven")

    return avg, above


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_columns = full_df.columns.tolist()

    print("Baseline (all features)...")
    baseline_avg, baseline_above = run_config(full_df, None, "BASELINE - all features")

    results = [("BASELINE", baseline_avg, baseline_above)]

    for category_name, base_names in FEATURE_CATEGORIES.items():
        cols_to_exclude = get_columns_for_category(all_columns, base_names)
        avg, above = run_config(full_df, cols_to_exclude, f"WITHOUT {category_name}")
        results.append((f"without {category_name}", avg, above))

    print("\n\n=== FINAL COMPARISON ===")
    print(f"{'Config':<35} {'Avg win rate':>14} {'Years above breakeven':>24}")
    for label, avg, above in results:
        print(f"{label:<35} {avg:>13.1f}% {above:>20}/4")


if __name__ == "__main__":
    run()