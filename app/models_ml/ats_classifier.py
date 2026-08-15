"""
Reframes the problem directly: predict whether HOME COVERS the opening
spread (binary classification), rather than predicting margin and
deriving edge afterward. This optimizes directly for the decision we
actually care about, rather than a proxy (MAE on raw margin, which
over-weights blowouts we don't bet on anyway).

Same walk-forward fold structure as ats_walkforward.py, for a fair
comparison against the regression approach.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss

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

CONFIDENCE_THRESHOLDS = [0.50, 0.55, 0.58, 0.60, 0.63]  # predicted prob away from 50/50
VIG_PRICE = -110

FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def prepare(df):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]  # drop pushes - no bet decision to grade
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS + MARKET_COLUMNS +
                     ["open_implied_margin", "margin_vs_open", "home_covers"]]
    return df, df[feature_cols], df["home_covers"], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    return 100 / abs(vig_price)


def run_fold(full_df, train_start, train_end, test_year):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    test_df = full_df[full_df["season"] == test_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_test, X_test, y_test, _ = prepare(test_df)

    if len(df_train) < 100 or len(df_test) < 30:
        return None, None

    model = xgb.XGBClassifier(random_state=42, eval_metric="logloss", **PARAMS)
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)[:, 1]  # P(home covers)
    acc = accuracy_score(y_test, probs > 0.5)
    ll = log_loss(y_test, probs)

    print(f"  Overall accuracy: {acc*100:.1f}% | Log loss: {ll:.3f}")

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

    return model, threshold_results, feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_results = {}
    last_model = None
    last_features = None

    for train_start, train_end, test_year in FOLDS:
        print(f"\n=== Fold: train {train_start}-{train_end}, test {test_year} ===")
        result = run_fold(full_df, train_start, train_end, test_year)
        if result[0] is None:
            print("  Skipped - insufficient data")
            continue
        model, threshold_results, feature_cols = result
        all_results[test_year] = threshold_results
        last_model, last_features = model, feature_cols

        for conf, data in threshold_results.items():
            if data is None:
                print(f"  Confidence>={conf}: no bets")
                continue
            n, wins, losses, win_rate, units = data
            print(f"  Confidence>={conf}: {n} bets, {win_rate:.1f}% win rate, {units:+.2f}u")

    print("\n\n=== SUMMARY: win rate by confidence threshold, across all test years ===")
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

    if last_model is not None:
        print("\n\n=== Top 15 feature importances (final fold's model) ===")
        importances = pd.Series(last_model.feature_importances_, index=last_features).sort_values(ascending=False)
        for feat, imp in importances.head(15).items():
            print(f"  {feat}: {imp:.4f}")


if __name__ == "__main__":
    run()