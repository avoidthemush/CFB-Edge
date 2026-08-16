"""
Answers a practical question we haven't checked yet: how many games PER
WEEK actually qualify as a bet under our full rule set (confidence>=0.60,
underdog only, non-neutral-site, week 5+)? A good win rate on almost no
games isn't a usable strategy.
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

    all_bets = []
    weeks_covered_by_year = {}

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

        bet_on_home = probs >= CONFIDENCE_THRESHOLD
        bet_on_away = probs <= (1 - CONFIDENCE_THRESHOLD)

        bet_df = df_test.copy()
        bet_df["confident"] = bet_on_home | bet_on_away
        bet_df["bet_on_home"] = bet_on_home
        bet_df["is_underdog_bet"] = (
            (bet_df["bet_on_home"] & (bet_df["market_spread_open"] > 0)) |
            (~bet_df["bet_on_home"] & (bet_df["market_spread_open"] < 0))
        )
        bet_df["qualifies"] = (
            bet_df["confident"] &
            bet_df["is_underdog_bet"] &
            (bet_df["neutral_site"] != True) &
            (bet_df["week"] >= 5)
        )
        bet_df["actual_home_covers"] = y_test.values.astype(bool)
        bet_df["won"] = bet_df["bet_on_home"] == bet_df["actual_home_covers"]

        # Total FBS games per week that season, for context
        weeks_covered_by_year[test_year] = df_test.groupby("week").size().to_dict()

        all_bets.append(bet_df[bet_df["qualifies"]])

    qualifying = pd.concat(all_bets, ignore_index=True)

    print(f"Total qualifying bets across all 4 test years: {len(qualifying)}\n")

    win_rate = qualifying["won"].mean() * 100
    print(f"Win rate on qualifying bets: {win_rate:.1f}%\n")

    print("=== Games per week that QUALIFY (all 4 years combined, then averaged) ===")
    per_week = qualifying.groupby(["season", "week"]).size().reset_index(name="qualifying_games")
    avg_per_week = per_week.groupby("week")["qualifying_games"].mean().round(1)
    total_fbs_per_week = pd.DataFrame(weeks_covered_by_year).mean(axis=1).round(1)

    print(f"{'Week':<6}{'Avg qualifying bets':>22}{'Avg total FBS games':>22}")
    for week in sorted(avg_per_week.index):
        qual = avg_per_week.get(week, 0)
        total = total_fbs_per_week.get(week, 0)
        print(f"{week:<6}{qual:>22.1f}{total:>22.1f}")

    print(f"\n=== Overall average qualifying bets per week (weeks 5+): {avg_per_week[avg_per_week.index >= 5].mean():.1f} ===")
    print(f"=== Overall average TOTAL FBS games per week: {total_fbs_per_week.mean():.1f} ===")


if __name__ == "__main__":
    run()