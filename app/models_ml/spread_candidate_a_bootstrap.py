"""
Final confirmatory test for Candidate A before considering it a
replacement for the currently locked feature set - same bootstrap
resampling rigor applied to the original Mid-Season Value Dog
validation, not skipped just because this result already looks good.
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
ID_COLUMNS = ["home_coach_id", "away_coach_id"]

CATEGORY_PATTERNS = {
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "raw_offense_defense_stats": ["off_success_rate", "off_explosiveness", "def_havoc_rate",
                                    "def_points_per_opportunity", "def_success_rate_allowed",
                                    "off_line_yards", "off_power_success", "def_stuff_rate",
                                    "off_ppa", "def_ppa"],
}

CONFIDENCE_THRESHOLD = 0.60
BREAKEVEN = 0.524
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]
N_BOOTSTRAP = 10000


def get_cols_for_category(all_columns, patterns):
    return [c for c in all_columns if any(p in c for p in patterns)]


def prepare(df, all_columns):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    keep = set(["neutral_site", "is_dome"])
    for patterns in CATEGORY_PATTERNS.values():
        keep.update(get_cols_for_category(all_columns, patterns))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    all_columns = full_df.columns.tolist()

    all_correct = []

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, all_columns)
        df_test, X_test, y_test, _ = prepare(test_df, all_columns)

        if len(df_train) < 100 or len(df_test) < 30:
            continue

        imputer = SimpleImputer(strategy="median")
        X_train_imp = imputer.fit_transform(X_train)
        X_test_imp = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imp)
        X_test_scaled = scaler.transform(X_test_imp)

        model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
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

    print(f"Total pooled bets: {n}")
    print(f"Observed win rate: {observed_rate:.1f}%\n")
    print(f"Running {N_BOOTSTRAP} bootstrap resamples...\n")

    rng = np.random.default_rng(42)
    bootstrap_rates = np.array([
        rng.choice(all_correct, size=n, replace=True).mean() * 100
        for _ in range(N_BOOTSTRAP)
    ])

    pct_above_breakeven = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
    pct_above_50 = (bootstrap_rates >= 50).mean() * 100
    ci_low, ci_high = np.percentile(bootstrap_rates, [2.5, 97.5])

    print(f"Mean resampled win rate: {bootstrap_rates.mean():.1f}%")
    print(f"95% confidence interval: [{ci_low:.1f}%, {ci_high:.1f}%]")
    print(f"% of resamples above 50%: {pct_above_50:.1f}%")
    print(f"% of resamples above 52.4% (breakeven): {pct_above_breakeven:.1f}%")
    print(f"\nFor comparison, ORIGINAL locked config bootstrap result: 85.6% of resamples profitable")


if __name__ == "__main__":
    run()