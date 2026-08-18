"""
Combines the FLB slight-dog zone (real, monotonic market pattern) with
our own model's agreement - only bet the underdog when BOTH (a) they're
a slight dog (spread 0-3) AND (b) our classifier also gives them a
reasonable win probability (not just the market's price, an independent
check). Real ROI, walk-forward across years.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

STAKE = 100
MIN_MODEL_PROB_FOR_DOG = [0.35, 0.40, 0.45, 0.50]
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


def prepare(df, all_columns):
    df = df[
        df["market_spread_open"].notna() & df["actual_spread"].notna() &
        df["market_home_moneyline"].notna() & df["market_away_moneyline"].notna()
    ].copy()
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

    for min_prob in MIN_MODEL_PROB_FOR_DOG:
        print(f"\n=== Require model's own dog-win-probability >= {min_prob} ===")
        pooled_profit, pooled_n, pooled_wins = 0, 0, 0

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
            df_test["home_is_dog"] = df_test["market_spread_open"] > 0
            df_test["dog_spread_size"] = df_test["market_spread_open"].abs()
            df_test["dog_ml"] = df_test.apply(lambda r: r["market_home_moneyline"] if r["home_is_dog"] else r["market_away_moneyline"], axis=1)
            df_test["dog_won"] = df_test.apply(lambda r: (r["actual_spread"] > 0) if r["home_is_dog"] else (r["actual_spread"] < 0), axis=1)
            df_test["our_dog_prob"] = df_test.apply(lambda r: r["our_home_prob"] if r["home_is_dog"] else 1 - r["our_home_prob"], axis=1)

            qualifying = df_test[
                (df_test["dog_spread_size"] >= 0) & (df_test["dog_spread_size"] < 3) &
                (df_test["our_dog_prob"] >= min_prob) & (df_test["market_spread_open"] != 0)
            ].copy()

            if len(qualifying) == 0:
                print(f"  {test_year}: no qualifying bets")
                continue

            qualifying["profit"] = qualifying.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
            win_rate = qualifying["dog_won"].mean() * 100
            profit = qualifying["profit"].sum()
            roi = profit / (len(qualifying) * STAKE) * 100
            marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
            print(f"  {test_year}: n={len(qualifying)}, win={win_rate:.1f}%, ${profit:+.0f} profit, ROI={roi:+.1f}%{marker}")

            pooled_profit += profit
            pooled_n += len(qualifying)
            pooled_wins += qualifying["dog_won"].sum()

        if pooled_n > 0:
            print(f"  POOLED: n={pooled_n}, win={pooled_wins/pooled_n*100:.1f}%, ROI={pooled_profit/(pooled_n*STAKE)*100:+.1f}%")


if __name__ == "__main__":
    run()