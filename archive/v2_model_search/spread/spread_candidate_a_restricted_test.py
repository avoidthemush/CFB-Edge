"""
Tests whether Candidate A's feature set improves when Mid-Season Value
Dog's situational rules (week>=5, underdog-only, non-neutral-site) are
layered on top - a real, previously-untested question, since Candidate A
has only ever been tested unrestricted (confidence>=0.60 only).
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

CANDIDATE_A_PATTERNS = {
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "raw_offense_defense_stats": ["off_success_rate", "off_explosiveness", "def_havoc_rate",
                                    "def_points_per_opportunity", "def_success_rate_allowed",
                                    "off_line_yards", "off_power_success", "def_stuff_rate",
                                    "off_ppa", "def_ppa"],
}

CONFIDENCE_THRESHOLD = 0.60
BREAKEVEN = 0.524
MIN_WEEK = 5
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


def run_fold(full_df, all_columns, patterns_list, train_start, train_end, test_year, apply_restrictions):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    test_df = full_df[full_df["season"] == test_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df, patterns_list, all_columns)
    df_test, X_test, y_test, _ = prepare(test_df, patterns_list, all_columns)

    if len(df_train) < 100 or len(df_test) < 30:
        return None

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_test_scaled)[:, 1]

    bet_on_home = probs >= 0.5
    confidence = np.where(bet_on_home, probs, 1 - probs)

    bet_mask = confidence >= CONFIDENCE_THRESHOLD

    if apply_restrictions:
        is_underdog_bet = (
            (bet_on_home & (df_test["market_spread_open"].values > 0)) |
            (~bet_on_home & (df_test["market_spread_open"].values < 0))
        )
        week_ok = df_test["week"].values >= MIN_WEEK
        not_neutral = df_test["neutral_site"].values != 1
        bet_mask = bet_mask & is_underdog_bet & week_ok & not_neutral

    if bet_mask.sum() == 0:
        return None

    actual_home_covers = y_test.values[bet_mask].astype(bool)
    predicted = bet_on_home[bet_mask]
    correct = predicted == actual_home_covers
    return correct.astype(int), int(correct.sum()), len(correct)


def run_variant(full_df, all_columns, patterns_list, apply_restrictions, label):
    all_correct = []
    pooled_wins = 0
    pooled_total = 0

    print(f"\n=== {label} ===")
    for train_start, train_end, test_year in FOLDS:
        result = run_fold(full_df, all_columns, patterns_list, train_start, train_end, test_year, apply_restrictions)
        if result is None:
            print(f"  {test_year}: no qualifying bets")
            continue
        correct_arr, wins, total = result
        all_correct.extend(correct_arr.tolist())
        pooled_wins += wins
        pooled_total += total
        rate = wins / total * 100
        marker = " <-- above breakeven" if rate >= 52.4 else ""
        print(f"  {test_year}: {wins}/{total} = {rate:.1f}%{marker}")

    if pooled_total == 0:
        print("  No bets at all")
        return

    pooled_rate = pooled_wins / pooled_total * 100
    pvalue = binomtest(pooled_wins, pooled_total, p=BREAKEVEN, alternative="greater").pvalue
    print(f"  POOLED: {pooled_wins}/{pooled_total} = {pooled_rate:.1f}% | p={pvalue:.4f}")

    all_correct = np.array(all_correct)
    rng = np.random.default_rng(42)
    bootstrap_rates = np.array([
        rng.choice(all_correct, size=len(all_correct), replace=True).mean() * 100
        for _ in range(N_BOOTSTRAP)
    ])
    pct_profitable = (bootstrap_rates >= BREAKEVEN * 100).mean() * 100
    print(f"  Bootstrap: {pct_profitable:.1f}% of resamples profitable")


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    all_columns = full_df.columns.tolist()
    patterns_list = list(CANDIDATE_A_PATTERNS.values())

    run_variant(full_df, all_columns, patterns_list, apply_restrictions=False,
                label="Candidate A UNRESTRICTED (as originally tested)")
    run_variant(full_df, all_columns, patterns_list, apply_restrictions=True,
                label="Candidate A + Mid-Season Value Dog rules (week>=5, underdog-only, non-neutral)")


if __name__ == "__main__":
    run()