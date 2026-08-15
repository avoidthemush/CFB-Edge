"""
Tests whether the SIZE of a favorite-side disagreement matters, not just
whether one exists. The earlier segment analysis found favorite bets
averaged ~50-51% (no edge) - but that blended small, weak disagreements
with large, strong ones. This checks if large favorite disagreements
specifically behave differently than small ones, the same way overall
confidence correlated with accuracy.
"""
import pandas as pd
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

# Finer-grained probability buckets than the original >=0.60 cutoff, to
# see if win rate climbs with confidence WITHIN the favorite-only subset
CONFIDENCE_BUCKETS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


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

    all_bets = []

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

        bet_df = df_test.copy()
        bet_df["prob"] = probs
        bet_df["bet_on_home"] = probs >= 0.5
        bet_df["confidence"] = bet_df["prob"].where(bet_df["bet_on_home"], 1 - bet_df["prob"])
        bet_df["is_favorite_bet"] = (
            (bet_df["bet_on_home"] & (bet_df["market_spread_open"] < 0)) |
            (~bet_df["bet_on_home"] & (bet_df["market_spread_open"] > 0))
        )
        bet_df["actual_home_covers"] = y_test.values.astype(bool)
        bet_df["won"] = bet_df["bet_on_home"] == bet_df["actual_home_covers"]

        all_bets.append(bet_df[bet_df["is_favorite_bet"]])

    favorite_bets = pd.concat(all_bets, ignore_index=True)
    print(f"Total favorite-side bets (all confidence levels): {len(favorite_bets)}\n")

    print("=== Win rate by confidence level, FAVORITE bets only ===")
    for low, high in CONFIDENCE_BUCKETS:
        bucket = favorite_bets[(favorite_bets["confidence"] >= low) & (favorite_bets["confidence"] < high)]
        if len(bucket) == 0:
            print(f"  {low:.2f}-{high:.2f}: no bets")
            continue
        win_rate = bucket["won"].mean() * 100
        marker = " <-- above breakeven" if win_rate >= 52.4 else ""
        print(f"  {low:.2f}-{high:.2f}: {len(bucket)} bets, {win_rate:.1f}% win rate{marker}")


if __name__ == "__main__":
    run()