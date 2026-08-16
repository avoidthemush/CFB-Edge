"""
Bootstrap resampling on the 'without recruiting' confidence>=0.60-0.63
result - the most promising finding tonight. Instead of trusting one
win-rate number, resamples the actual bet outcomes thousands of times
(with replacement) to see how consistently the win rate stays above
breakeven. More rigorous than a single point estimate.
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
ID_COLUMNS = ["home_coach_id", "away_coach_id"]
RECRUITING_COLS = [
    "home_recruiting_rank", "away_recruiting_rank", "diff_recruiting_rank",
    "home_recruiting_points", "away_recruiting_points", "diff_recruiting_points",
    "home_off_new_talent_impact", "away_off_new_talent_impact", "diff_off_new_talent_impact",
    "home_def_new_talent_impact", "away_def_new_talent_impact", "diff_def_new_talent_impact",
    "talent_edge_early_season", "recruiting_edge_early_season",
]

CONFIDENCE_THRESHOLD = 0.60
BREAKEVEN = 0.524
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]
N_BOOTSTRAP = 10000


def prepare(df, exclude_cols):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    base_exclude = NON_FEATURE_COLUMNS + MARKET_COLUMNS + ID_COLUMNS + exclude_cols + \
                   ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in df.columns if c not in base_exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    exclude = [c for c in RECRUITING_COLS if c in full_df.columns]

    all_correct = []  # 1 = bet won, 0 = bet lost, across ALL folds pooled

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude)
        df_test, X_test, y_test, _ = prepare(test_df, exclude)

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
        correct = (predicted_home_covers == actual_home_covers.astype(bool)).astype(int)
        all_correct.extend(correct.tolist())

    all_correct = np.array(all_correct)
    n = len(all_correct)
    observed_rate = all_correct.mean() * 100

    print(f"Total pooled bets across all folds: {n}")
    print(f"Observed win rate: {observed_rate:.1f}%")
    print(f"\nRunning {N_BOOTSTRAP} bootstrap resamples...\n")

    rng = np.random.default_rng(42)
    bootstrap_rates = []
    for _ in range(N_BOOTSTRAP):
        sample = rng.choice(all_correct, size=n, replace=True)
        bootstrap_rates.append(sample.mean() * 100)

    bootstrap_rates = np.array(bootstrap_rates)

    pct_above_breakeven = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
    pct_above_50 = (bootstrap_rates >= 50).mean() * 100

    ci_low, ci_high = np.percentile(bootstrap_rates, [2.5, 97.5])

    print(f"Bootstrap results:")
    print(f"  Mean resampled win rate: {bootstrap_rates.mean():.1f}%")
    print(f"  95% confidence interval: [{ci_low:.1f}%, {ci_high:.1f}%]")
    print(f"  % of resamples above 50% (pure chance): {pct_above_50:.1f}%")
    print(f"  % of resamples above 52.4% (breakeven):  {pct_above_breakeven:.1f}%")
    print(f"\nIn plain terms: if we re-ran this 'experiment' {N_BOOTSTRAP} times with the same")
    print(f"underlying bets shuffled randomly, {pct_above_breakeven:.1f}% of the time we'd still")
    print(f"see a profitable win rate. {'That is strong, consistent evidence.' if pct_above_breakeven > 90 else 'That leaves real, meaningful doubt.' if pct_above_breakeven < 80 else 'That is suggestive but not fully conclusive.'}")


if __name__ == "__main__":
    run()