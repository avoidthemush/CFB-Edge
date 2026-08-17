"""
Walk-forward linear-weights test on the RESTRUCTURED feature set:
offense-vs-defense matchups (not offense-vs-offense), trenches,
returning-production+talent interaction, coach quality/H2H - replacing
the face-value stat diffs tested earlier tonight. Same walk-forward
folds, same significance testing, same coefficient-stability check, for
a direct, fair comparison against the original results.
"""
import pandas as pd
import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score

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
BREAKEVEN = 0.524

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

    # coach_id columns are identifiers, not features
    id_cols = [c for c in df.columns if c in ["home_coach_id", "away_coach_id"]]

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS + MARKET_COLUMNS + id_cols +
                     ["open_implied_margin", "margin_vs_open", "home_covers"]]
    return df, df[feature_cols], df["home_covers"], feature_cols


def units_won_per_bet(vig_price=VIG_PRICE):
    return 100 / abs(vig_price)


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_coefs = []
    fold_labels = []
    pooled_wins = 0
    pooled_total = 0
    all_summary = {}

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df)
        df_test, X_test, y_test, _ = prepare(test_df)

        if len(df_train) < 100 or len(df_test) < 30:
            print(f"\n{test_year}: skipped - insufficient data")
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

        acc = accuracy_score(y_test, probs > 0.5)
        print(f"\n=== {test_year} === (train {train_start}-{train_end}, {len(X_train)} rows | test {len(X_test)} rows)")
        print(f"  Overall accuracy: {acc*100:.1f}%")

        year_results = {}
        for conf in CONFIDENCE_THRESHOLDS:
            confident_home = probs >= conf
            confident_away = probs <= (1 - conf)
            bet_mask = confident_home | confident_away

            if bet_mask.sum() == 0:
                year_results[conf] = None
                continue

            predicted_home_covers = confident_home[bet_mask]
            actual_home_covers = y_test.values[bet_mask]
            correct = predicted_home_covers == actual_home_covers.astype(bool)
            wins = int(correct.sum())
            total = len(correct)
            win_rate = wins / total * 100

            if conf == 0.60:
                pooled_wins += wins
                pooled_total += total

            print(f"  Confidence>={conf}: {total} bets, {win_rate:.1f}% win rate")
            year_results[conf] = (total, wins, win_rate)

        all_summary[test_year] = year_results

        coef_series = pd.Series(model.coef_[0], index=feature_cols)
        all_coefs.append(coef_series)
        fold_labels.append(test_year)

    print("\n\n=== SUMMARY: win rate by confidence threshold, across all years ===")
    for conf in CONFIDENCE_THRESHOLDS:
        rates = []
        for year, results in all_summary.items():
            data = results.get(conf)
            if data:
                rates.append((year, data[2], data[0]))
        if rates:
            print(f"\nConfidence >= {conf}:")
            for year, rate, n in rates:
                marker = " <-- above breakeven" if rate >= 52.4 else ""
                print(f"    {year}: {rate:.1f}% (n={n}){marker}")
            avg = sum(r for _, r, _ in rates) / len(rates)
            above = sum(1 for _, r, _ in rates if r >= 52.4)
            print(f"    AVG: {avg:.1f}% | {above}/{len(rates)} years above breakeven")

    print("\n\n=== Significance check at confidence >= 0.60 (pooled) ===")
    if pooled_total > 0:
        vs_chance = binomtest(pooled_wins, pooled_total, p=0.5, alternative="greater")
        vs_breakeven = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater")
        print(f"Pooled: {pooled_wins}/{pooled_total} = {pooled_wins/pooled_total*100:.1f}%")
        print(f"  vs 50%: p={vs_chance.pvalue:.4f} | vs 52.4%: p={vs_breakeven.pvalue:.4f}")

    print("\n\n=== Coefficient stability across folds (top 20 by avg magnitude) ===")
    if len(all_coefs) >= 2:
        coef_df = pd.concat(all_coefs, axis=1)
        coef_df.columns = fold_labels
        avg_abs = coef_df.abs().mean(axis=1).sort_values(ascending=False)
        top_features = avg_abs.head(20).index

        print(f"\n{'Feature':<45}" + "".join(f"{y:>9}" for y in fold_labels) + f"{'Stable?':>10}")
        for feat in top_features:
            row = coef_df.loc[feat]
            signs = np.sign(row)
            consistent = "YES" if len(set(signs)) == 1 else "NO"
            print(f"{feat:<45}" + "".join(f"{v:>9.3f}" for v in row) + f"{consistent:>10}")

        flip_count = sum(1 for feat in top_features if len(set(np.sign(coef_df.loc[feat]))) > 1)
        print(f"\n{flip_count}/{len(top_features)} top features flip sign across folds")

        matchup_features = [f for f in top_features if "matchup" in f]
        print(f"\nMatchup-based features in top 20: {len(matchup_features)}")
        for f in matchup_features:
            print(f"  {f}")


if __name__ == "__main__":
    run()