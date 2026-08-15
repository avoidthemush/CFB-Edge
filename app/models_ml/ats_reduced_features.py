"""
Tests whether trimming to only the most consistently important features
(aggregated importance across ALL walk-forward folds, not just one)
improves stability/accuracy versus the full 64-feature set. Same
classifier approach and fold structure as ats_classifier.py, for a fair
comparison.
"""
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from collections import defaultdict

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

CONFIDENCE_THRESHOLDS = [0.50, 0.55, 0.58, 0.60, 0.63]
VIG_PRICE = -110
TOP_N_FEATURES = 20

FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def prepare(df, feature_subset=None):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    if feature_subset:
        feature_cols = feature_subset
    else:
        feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS + MARKET_COLUMNS +
                         ["open_implied_margin", "margin_vs_open", "home_covers"]]
    return df, df[feature_cols], df["home_covers"], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    return 100 / abs(vig_price)


def get_aggregate_importance(full_df):
    """First pass: train on all folds with full feature set, average importance across folds."""
    importance_sums = defaultdict(float)
    importance_counts = defaultdict(int)

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        df_train, X_train, y_train, feature_cols = prepare(train_df)
        if len(df_train) < 100:
            continue

        model = xgb.XGBClassifier(random_state=42, eval_metric="logloss", **PARAMS)
        model.fit(X_train, y_train)

        for feat, imp in zip(feature_cols, model.feature_importances_):
            importance_sums[feat] += imp
            importance_counts[feat] += 1

    avg_importance = {f: importance_sums[f] / importance_counts[f] for f in importance_sums}
    return sorted(avg_importance.items(), key=lambda x: -x[1])


def run_fold(full_df, train_start, train_end, test_year, feature_subset):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    test_df = full_df[full_df["season"] == test_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df, feature_subset)
    df_test, X_test, y_test, _ = prepare(test_df, feature_subset)

    if len(df_train) < 100 or len(df_test) < 30:
        return None

    model = xgb.XGBClassifier(random_state=42, eval_metric="logloss", **PARAMS)
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, probs > 0.5)
    print(f"  Overall accuracy: {acc*100:.1f}%")

    win_unit = units_won_per_bet()
    threshold_results = {}

    for conf in CONFIDENCE_THRESHOLDS:
        confident_home = probs >= conf
        confident_away = probs <= (1 - conf)
        bet_mask = confident_home | confident_away

        if bet_mask.sum() == 0:
            threshold_results[conf] = None
            continue

        predicted_home_covers = confident_home[bet_mask]
        actual_home_covers = y_test.values[bet_mask]
        correct = predicted_home_covers == actual_home_covers.astype(bool)

        wins = correct.sum()
        losses = (~correct).sum()
        win_rate = wins / len(correct) * 100
        units = wins * win_unit - losses * 1.0

        threshold_results[conf] = (bet_mask.sum(), wins, losses, win_rate, units)

    return threshold_results


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    print("=== Computing aggregate feature importance across all folds ===")
    ranked_features = get_aggregate_importance(full_df)
    top_features = [f for f, _ in ranked_features[:TOP_N_FEATURES]]

    print(f"\nTop {TOP_N_FEATURES} features by average importance:")
    for feat, imp in ranked_features[:TOP_N_FEATURES]:
        print(f"  {feat}: {imp:.4f}")

    print(f"\n\n=== Re-running walk-forward with ONLY top {TOP_N_FEATURES} features ===")
    all_results = {}

    for train_start, train_end, test_year in FOLDS:
        print(f"\n=== Fold: train {train_start}-{train_end}, test {test_year} ===")
        result = run_fold(full_df, train_start, train_end, test_year, top_features)
        if result is None:
            print("  Skipped - insufficient data")
            continue
        all_results[test_year] = result
        for conf, data in result.items():
            if data is None:
                print(f"  Confidence>={conf}: no bets")
                continue
            n, wins, losses, win_rate, units = data
            print(f"  Confidence>={conf}: {n} bets, {win_rate:.1f}% win rate, {units:+.2f}u")

    print("\n\n=== SUMMARY (reduced features): win rate by confidence threshold ===")
    for conf in CONFIDENCE_THRESHOLDS:
        rates = []
        for year, result in all_results.items():
            data = result.get(conf)
            if data:
                rates.append((year, data[3], data[0]))
        if rates:
            print(f"\nConfidence >= {conf}:")
            for year, rate, n in rates:
                marker = " <-- above breakeven" if rate >= 52.4 else ""
                print(f"    {year}: {rate:.1f}% (n={n}){marker}")
            avg_rate = sum(r for _, r, _ in rates) / len(rates)
            above = sum(1 for _, r, _ in rates if r >= 52.4)
            print(f"    AVG: {avg_rate:.1f}% | {above}/{len(rates)} years above breakeven")


if __name__ == "__main__":
    run()