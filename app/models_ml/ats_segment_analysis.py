"""
Check 2: breaks the 'without recruiting, confidence>=0.60' bets down by
situation (favorite/underdog, early/late season, spread size) to see if
the overall win rate is hiding a more specific, stronger (or weaker)
pattern within it.
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

CONFIDENCE_THRESHOLD = 0.60
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

    all_bets = []  # list of dicts: one per bet, with outcome + segment info

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

        bet_df = df_test[bet_mask].copy()
        bet_df["bet_on_home"] = confident_home[bet_mask]
        bet_df["actual_home_covers"] = y_test.values[bet_mask].astype(bool)
        bet_df["won"] = bet_df["bet_on_home"] == bet_df["actual_home_covers"]
        all_bets.append(bet_df)

    bets = pd.concat(all_bets, ignore_index=True)
    print(f"Total bets analyzed: {len(bets)}\n")

    def report(label, mask):
        subset = bets[mask]
        if len(subset) == 0:
            print(f"{label}: no bets")
            return
        win_rate = subset["won"].mean() * 100
        marker = " <-- above breakeven" if win_rate >= 52.4 else ""
        print(f"{label}: {len(subset)} bets, {win_rate:.1f}% win rate{marker}")

    print("=== By favorite/underdog (were we betting the HOME favorite or HOME underdog) ===")
    report("Bet on home, home is favorite (market_spread_open < 0)", bets["bet_on_home"] & (bets["market_spread_open"] < 0))
    report("Bet on home, home is underdog (market_spread_open > 0)", bets["bet_on_home"] & (bets["market_spread_open"] > 0))
    report("Bet on away, away is favorite (market_spread_open > 0)", ~bets["bet_on_home"] & (bets["market_spread_open"] > 0))
    report("Bet on away, away is underdog (market_spread_open < 0)", ~bets["bet_on_home"] & (bets["market_spread_open"] < 0))

    print("\n=== By season timing ===")
    report("Weeks 1-4 (early season)", bets["week"] <= 4)
    report("Weeks 5-9 (mid season)", (bets["week"] > 4) & (bets["week"] <= 9))
    report("Weeks 10+ (late season)", bets["week"] > 9)

    print("\n=== By spread size (how big was the opening line) ===")
    report("Close games (|open spread| <= 7)", bets["market_spread_open"].abs() <= 7)
    report("Medium games (7 < |open spread| <= 14)", (bets["market_spread_open"].abs() > 7) & (bets["market_spread_open"].abs() <= 14))
    report("Big spreads (|open spread| > 14)", bets["market_spread_open"].abs() > 14)

    print("\n=== By neutral site vs home/away ===")
    report("Neutral site games", bets["neutral_site"] == True)
    report("Regular home/away games", bets["neutral_site"] != True)


if __name__ == "__main__":
    run()