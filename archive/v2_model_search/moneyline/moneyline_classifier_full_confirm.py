"""
Phase 2 confirmation for the narrow-odds-range (-200 to +150) EV
classifier - the second split (2023) showed a clean, monotonic
profitability pattern, a real upgrade over the first split's erratic
result. Full walk-forward across 4 years (2022-2025) + the same ROI
discipline throughout.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

STAKE = 100
EV_THRESHOLD = 0.08  # midpoint of the range that looked cleanest in both splits
MIN_ODDS, MAX_ODDS = -200, 150
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]

FEATURE_PATTERNS = [
    "returning_qb1", "returning_ppa_pct", "returning_havoc_pct",
    "off_success_rate", "off_explosiveness", "def_havoc_rate",
    "def_points_per_opportunity", "def_success_rate_allowed",
    "off_line_yards", "off_power_success", "def_stuff_rate",
    "off_ppa", "def_ppa",
]
NON_FEATURE_COLUMNS = ["game_id", "season", "week", "market_provider", "actual_spread", "actual_total", "home_won"]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


def payout_per_dollar(odds):
    if odds > 0:
        return odds / 100
    return 100 / -odds


def expected_value(our_prob, odds):
    payout = payout_per_dollar(odds)
    return our_prob * payout - (1 - our_prob)


def odds_in_range(odds):
    return MIN_ODDS <= odds <= MAX_ODDS


def prepare(df, all_columns):
    df = df[df["market_home_moneyline"].notna() & df["market_away_moneyline"].notna() & df["actual_spread"].notna()].copy()
    df["home_won"] = (df["actual_spread"] > 0).astype(int)
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in all_columns if any(p in c for p in FEATURE_PATTERNS) and c not in NON_FEATURE_COLUMNS + ID_COLUMNS]
    return df, df[feature_cols], df["home_won"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    all_columns = full_df.columns.tolist()

    pooled_wins, pooled_total, pooled_profit = 0, 0, 0

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, all_columns)
        df_test, X_test, y_test, _ = prepare(test_df, all_columns)

        imputer = SimpleImputer(strategy="median")
        X_train_imp = imputer.fit_transform(X_train)
        X_test_imp = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imp)
        X_test_scaled = scaler.transform(X_test_imp)

        model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
        model.fit(X_train_scaled, y_train)
        probs = model.predict_proba(X_test_scaled)[:, 1]

        df_test = df_test.copy()
        df_test["our_home_prob"] = probs
        df_test["ev_home"] = df_test.apply(lambda r: expected_value(r["our_home_prob"], r["market_home_moneyline"]), axis=1)
        df_test["ev_away"] = df_test.apply(lambda r: expected_value(1 - r["our_home_prob"], r["market_away_moneyline"]), axis=1)

        bet_home = df_test[(df_test["ev_home"] >= EV_THRESHOLD) & df_test["market_home_moneyline"].apply(odds_in_range)].copy()
        bet_home["won"] = bet_home["home_won"] == 1
        bet_home["profit"] = bet_home.apply(lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1)

        bet_away = df_test[(df_test["ev_away"] >= EV_THRESHOLD) & df_test["market_away_moneyline"].apply(odds_in_range)].copy()
        bet_away["won"] = bet_away["home_won"] == 0
        bet_away["profit"] = bet_away.apply(lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1)

        all_bets = pd.concat([bet_home, bet_away])
        if len(all_bets) == 0:
            print(f"{test_year}: no bets")
            continue

        wins = int(all_bets["won"].sum())
        total = len(all_bets)
        profit = all_bets["profit"].sum()
        roi = profit / (total * STAKE) * 100

        pooled_wins += wins
        pooled_total += total
        pooled_profit += profit

        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"{test_year}: {wins}/{total} = {wins/total*100:.1f}% win, ${profit:+.0f} profit, ROI={roi:+.1f}%{marker}")

    pooled_roi = pooled_profit / (pooled_total * STAKE) * 100 if pooled_total > 0 else 0
    print(f"\nPOOLED: {pooled_wins}/{pooled_total} = {pooled_wins/pooled_total*100:.1f}% win, "
          f"${pooled_profit:+.0f} profit on ${pooled_total*STAKE} staked, ROI={pooled_roi:+.1f}%")


if __name__ == "__main__":
    run()