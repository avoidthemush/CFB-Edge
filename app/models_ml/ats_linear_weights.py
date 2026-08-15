"""
Tests a fundamentally different approach: logistic regression (L2
regularized), which assigns one explicit, stable WEIGHT per feature,
rather than XGBoost's tree-split-based pattern finding. Better suited
to a modest number of true underlying signals (team strength, coaching,
talent, efficiency) spread across many correlated columns (SP+/Elo/PPA
all measure similar things) - correlated inputs tend to confuse tree
importance, but regularized linear weights handle them more gracefully.

Same walk-forward folds, same target, same breakeven bar as every other
test tonight - apples-to-apples comparison.
"""
import pandas as pd
import numpy as np
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

CONFIDENCE_THRESHOLDS = [0.50, 0.55, 0.58, 0.60, 0.63]
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
    df = df[df["margin_vs_open"] != 0]
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
        return None, None, None

    # Linear models need complete, scaled data - impute missing with the
    # training set's median (fit on train only, applied to both - no leakage)
    imputer = SimpleImputer(strategy="median")
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)

    model = LogisticRegression(max_iter=2000, C=0.1, random_state=42)  # C=0.1 = strong regularization
    model.fit(X_train_scaled, y_train)

    probs = model.predict_proba(X_test_scaled)[:, 1]
    acc = (probs > 0.5).astype(int).mean() == y_test.mean()  # placeholder, real acc below
    from sklearn.metrics import accuracy_score
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

    coef_series = pd.Series(model.coef_[0], index=feature_cols)
    return threshold_results, coef_series, feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_results = {}
    last_coefs = None

    for train_start, train_end, test_year in FOLDS:
        print(f"\n=== Fold: train {train_start}-{train_end}, test {test_year} ===")
        result = run_fold(full_df, train_start, train_end, test_year)
        if result[0] is None:
            print("  Skipped - insufficient data")
            continue
        threshold_results, coefs, feature_cols = result
        all_results[test_year] = threshold_results
        last_coefs = coefs

        for conf, data in threshold_results.items():
            if data is None:
                print(f"  Confidence>={conf}: no bets")
                continue
            n, wins, losses, win_rate, units = data
            print(f"  Confidence>={conf}: {n} bets, {win_rate:.1f}% win rate, {units:+.2f}u")

    print("\n\n=== SUMMARY (logistic regression / linear weights): win rate by confidence threshold ===")
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

    if last_coefs is not None:
        print("\n\n=== Top 15 weights by magnitude (final fold, positive = favors home covering) ===")
        top = last_coefs.reindex(last_coefs.abs().sort_values(ascending=False).index).head(15)
        for feat, weight in top.items():
            print(f"  {feat}: {weight:+.3f}")


if __name__ == "__main__":
    run()