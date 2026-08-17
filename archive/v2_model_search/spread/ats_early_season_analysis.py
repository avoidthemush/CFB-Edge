"""
Two direct tests of the user's hypothesis:
1. Week-by-week breakdown (1, 2, 3, 4 SEPARATELY, not lumped) - is there
   a specific early week that already works, hidden inside the weak
   average?
2. Ablation restricted to weeks 1-4 ONLY: does removing coach-quality
   features or returning-production features hurt early-week accuracy
   specifically? If removing them hurts a lot, they're already doing
   real work early - if removing them barely matters, they're not being
   used effectively yet, and that's a real gap to fix.
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
COACH_QUALITY_COLS = [
    "home_coach_career_win_pct", "away_coach_career_win_pct", "diff_coach_career_win_pct",
    "home_coach_career_avg_sp", "away_coach_career_avg_sp", "diff_coach_career_avg_sp",
    "home_coach_experience_seasons", "away_coach_experience_seasons", "diff_coach_experience_seasons",
]
RETURNING_PROD_COLS = [
    "home_off_returning_ppa_pct", "away_off_returning_ppa_pct", "diff_off_returning_ppa_pct",
    "home_def_returning_havoc_pct", "away_def_returning_havoc_pct", "diff_def_returning_havoc_pct",
]

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


def train_and_get_predictions(full_df, exclude_cols):
    """Trains per-fold (as always), returns ALL predictions (not just qualifying bets) with metadata."""
    all_preds = []
    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude_cols)
        df_test, X_test, y_test, _ = prepare(test_df, exclude_cols)

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

        result = df_test.copy()
        result["prob"] = probs
        result["bet_on_home"] = probs >= 0.5
        result["confidence"] = result["prob"].where(result["bet_on_home"], 1 - result["prob"])
        result["is_underdog_bet"] = (
            (result["bet_on_home"] & (result["market_spread_open"] > 0)) |
            (~result["bet_on_home"] & (result["market_spread_open"] < 0))
        )
        result["actual_home_covers"] = y_test.values.astype(bool)
        result["won"] = result["bet_on_home"] == result["actual_home_covers"]
        all_preds.append(result)

    return pd.concat(all_preds, ignore_index=True)


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    exclude = [c for c in RECRUITING_COLS if c in full_df.columns]

    print("=" * 70)
    print("PART 1: Week-by-week breakdown, weeks 1-4 SEPARATELY (underdog rule)")
    print("=" * 70)

    preds = train_and_get_predictions(full_df, exclude)
    qualifying = preds[
        (preds["confidence"] >= 0.60) &
        preds["is_underdog_bet"] &
        (preds["neutral_site"] != True)
    ]

    for week in [1, 2, 3, 4]:
        week_bets = qualifying[qualifying["week"] == week]
        if len(week_bets) == 0:
            print(f"  Week {week}: no qualifying bets")
            continue
        win_rate = week_bets["won"].mean() * 100
        marker = " <-- above breakeven" if win_rate >= 52.4 else ""
        print(f"  Week {week}: {len(week_bets)} bets, {win_rate:.1f}% win rate{marker}")

    print("\n\n" + "=" * 70)
    print("PART 2: Does removing coach-quality or returning-production hurt WEEKS 1-4 specifically?")
    print("=" * 70)

    configs = [
        ("FULL SET (minus recruiting, as established)", exclude),
        ("WITHOUT coach quality too", exclude + [c for c in COACH_QUALITY_COLS if c in full_df.columns]),
        ("WITHOUT returning production too", exclude + [c for c in RETURNING_PROD_COLS if c in full_df.columns]),
        ("WITHOUT both coach quality AND returning production",
         exclude + [c for c in COACH_QUALITY_COLS + RETURNING_PROD_COLS if c in full_df.columns]),
    ]

    for label, cols_to_exclude in configs:
        preds = train_and_get_predictions(full_df, cols_to_exclude)
        early_preds = preds[preds["week"] <= 4]
        early_qualifying = early_preds[
            (early_preds["confidence"] >= 0.60) &
            early_preds["is_underdog_bet"] &
            (early_preds["neutral_site"] != True)
        ]

        # Also report plain accuracy on ALL weeks 1-4 games (not just
        # qualifying bets) - tells us if the underlying prediction
        # quality changes, even before applying the betting filter
        early_all_correct = (early_preds["bet_on_home"] == early_preds["actual_home_covers"]).mean() * 100

        print(f"\n=== {label} ===")
        print(f"  Weeks 1-4, ALL games, plain accuracy: {early_all_correct:.1f}%")
        if len(early_qualifying) > 0:
            win_rate = early_qualifying["won"].mean() * 100
            print(f"  Weeks 1-4, qualifying underdog bets: {len(early_qualifying)} bets, {win_rate:.1f}% win rate")
        else:
            print(f"  Weeks 1-4, qualifying underdog bets: none")


if __name__ == "__main__":
    run()