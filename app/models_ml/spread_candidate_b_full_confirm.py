"""
Phase 2 confirmation for Candidate B (returning_qb + returning_production
+ coach_quality + weather + recent_form) - full 4-fold walk-forward
(touches 2025, spent deliberately) + bootstrap, same standard applied to
Candidate A before it was promoted.
"""
import pandas as pd
import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]

CANDIDATE_B_PATTERNS = {
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "coach_quality": ["coach_career_win_pct", "coach_career_avg_sp", "coach_experience_seasons",
                       "coach_upgrade_score"],
    "weather": ["temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate"],
    "recent_form": ["last_game_margin", "days_since_last_game"],
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


def get_cols_for_patterns(all_columns, patterns):
    return [c for c in all_columns if any(p in c for p in patterns)]


def prepare(df, patterns_list, all_columns):
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
    for patterns in patterns_list:
        keep.update(get_cols_for_patterns(all_columns, patterns))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    all_columns = full_df.columns.tolist()
    patterns_list = list(CANDIDATE_B_PATTERNS.values())

    all_correct = []
    pooled_wins = 0
    pooled_total = 0

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, patterns_list, all_columns)
        df_test, X_test, y_test, _ = prepare(test_df, patterns_list, all_columns)

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
        correct = predicted_home_covers == actual_home_covers.astype(bool)
        wins = int(correct.sum())
        total = len(correct)

        pooled_wins += wins
        pooled_total += total
        all_correct.extend(correct.astype(int).tolist())

        marker = " <-- above breakeven" if wins/total*100 >= 52.4 else ""
        print(f"{test_year}: {wins}/{total} = {wins/total*100:.1f}%{marker}")

    pooled_rate = pooled_wins / pooled_total * 100
    pvalue = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater").pvalue
    print(f"\nPOOLED: {pooled_wins}/{pooled_total} = {pooled_rate:.1f}% | p={pvalue:.4f}")

    all_correct = np.array(all_correct)
    rng = np.random.default_rng(42)
    bootstrap_rates = np.array([
        rng.choice(all_correct, size=len(all_correct), replace=True).mean() * 100
        for _ in range(N_BOOTSTRAP)
    ])
    pct_above_breakeven = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
    ci_low, ci_high = np.percentile(bootstrap_rates, [2.5, 97.5])

    print(f"Bootstrap: {pct_above_breakeven:.1f}% of resamples profitable, 95% CI [{ci_low:.1f}%, {ci_high:.1f}%]")
    print(f"\nFor comparison - Candidate A: 4/4 years, pooled 55.3%, p=0.0383, bootstrap 96.2% profitable")


if __name__ == "__main__":
    run()