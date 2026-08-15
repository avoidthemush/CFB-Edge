"""
Stress-tests the linear-weights confidence>=0.6 result specifically,
since it's the one candidate tonight that looked genuinely different
from everything else - which means it deserves MORE scrutiny, not less,
before we trust it.

Two checks:
1. Statistical significance - is each fold's win rate actually
   distinguishable from chance (50%) and from breakeven (52.4%), given
   the actual sample size, or still plausibly noise?
2. Coefficient stability across folds - if the model is finding a real
   pattern, the top-weighted features should look similar fold to fold
   (same sign, similar magnitude), not reshuffle each time.
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

CONFIDENCE_THRESHOLD = 0.60  # the specific threshold that looked promising
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

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS + MARKET_COLUMNS +
                     ["open_implied_margin", "margin_vs_open", "home_covers"]]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    all_coefs = []
    fold_labels = []
    pooled_wins = 0
    pooled_total = 0

    print("=" * 70)
    print("PART 1: Significance check at confidence >= 0.60")
    print("=" * 70)

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df)
        df_test, X_test, y_test, _ = prepare(test_df)

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
            print(f"\n{test_year}: no qualifying bets")
            continue

        predicted_home_covers = confident_home[bet_mask]
        actual_home_covers = y_test.values[bet_mask]
        correct = predicted_home_covers == actual_home_covers.astype(bool)
        wins = int(correct.sum())
        total = len(correct)
        win_rate = wins / total

        pooled_wins += wins
        pooled_total += total

        vs_chance = binomtest(wins, total, p=0.5, alternative="greater")
        vs_breakeven = binomtest(wins, total, p=BREAKEVEN, alternative="greater")

        print(f"\n{test_year}: {wins}/{total} = {win_rate*100:.1f}%")
        print(f"  vs. 50% (pure chance):    p-value = {vs_chance.pvalue:.4f} "
              f"({'significant at p<0.05' if vs_chance.pvalue < 0.05 else 'NOT significant'})")
        print(f"  vs. 52.4% (breakeven):    p-value = {vs_breakeven.pvalue:.4f} "
              f"({'significant at p<0.05' if vs_breakeven.pvalue < 0.05 else 'NOT significant'})")

        coef_series = pd.Series(model.coef_[0], index=feature_cols)
        all_coefs.append(coef_series)
        fold_labels.append(test_year)

    print(f"\n\n--- POOLED across all {len(fold_labels)} folds (directional check only - each fold uses a different trained model, so this is illustrative, not a clean statistical test) ---")
    if pooled_total > 0:
        pooled_rate = pooled_wins / pooled_total
        pooled_vs_chance = binomtest(pooled_wins, pooled_total, p=0.5, alternative="greater")
        pooled_vs_breakeven = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater")
        print(f"Pooled: {pooled_wins}/{pooled_total} = {pooled_rate*100:.1f}%")
        print(f"  vs. 50%: p-value = {pooled_vs_chance.pvalue:.4f}")
        print(f"  vs. 52.4%: p-value = {pooled_vs_breakeven.pvalue:.4f}")

    print("\n\n" + "=" * 70)
    print("PART 2: Coefficient stability across folds")
    print("=" * 70)

    if len(all_coefs) >= 2:
        coef_df = pd.concat(all_coefs, axis=1)
        coef_df.columns = fold_labels

        # Rank features by average absolute weight across folds
        avg_abs = coef_df.abs().mean(axis=1).sort_values(ascending=False)
        top_features = avg_abs.head(15).index

        print(f"\n{'Feature':<35}" + "".join(f"{y:>10}" for y in fold_labels) + f"{'Sign consistent?':>20}")
        for feat in top_features:
            row = coef_df.loc[feat]
            signs = np.sign(row)
            consistent = "YES" if len(set(signs)) == 1 else "NO - flips sign"
            print(f"{feat:<35}" + "".join(f"{v:>10.3f}" for v in row) + f"{consistent:>20}")

        flip_count = sum(1 for feat in top_features if len(set(np.sign(coef_df.loc[feat]))) > 1)
        print(f"\n{flip_count}/{len(top_features)} top features flip sign across folds "
              f"({'CONCERNING - suggests unstable/noisy weights' if flip_count > len(top_features) * 0.3 else 'reasonably stable'})")


if __name__ == "__main__":
    run()