"""
Re-tests EV-based betting with an odds range cap (-300 to +300) to
exclude extreme longshots, where a small amount of honest model
imprecision gets amplified by large payout multipliers into fake-
looking EV (confirmed directly: EV-qualifying bets were 69-91%
underdogs, avg away odds +430 vs overall average +32).
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

STAKE = 100
EV_THRESHOLDS = [0.02, 0.05, 0.08, 0.10, 0.15]
MIN_ODDS, MAX_ODDS = -300, 300

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
    full_df = full_df[full_df["season"] <= 2024]
    all_columns = full_df.columns.tolist()

    train_df = full_df[(full_df["season"] >= 2021) & (full_df["season"] <= 2023)]
    val_df = full_df[full_df["season"] == 2024]

    df_train, X_train, y_train, feature_cols = prepare(train_df, all_columns)
    df_val, X_val, y_val, _ = prepare(val_df, all_columns)

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_val_scaled)[:, 1]

    df_val = df_val.copy()
    df_val["our_home_prob"] = probs
    df_val["ev_home"] = df_val.apply(lambda r: expected_value(r["our_home_prob"], r["market_home_moneyline"]), axis=1)
    df_val["ev_away"] = df_val.apply(lambda r: expected_value(1 - r["our_home_prob"], r["market_away_moneyline"]), axis=1)

    print(f"Odds cap: {MIN_ODDS} to {MAX_ODDS}\n")
    print("=== Results by EV threshold, odds-capped ===")
    for threshold in EV_THRESHOLDS:
        bet_home = df_val[(df_val["ev_home"] >= threshold) & df_val["market_home_moneyline"].apply(odds_in_range)].copy()
        bet_home["won"] = bet_home["home_won"] == 1
        bet_home["profit"] = bet_home.apply(lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1)

        bet_away = df_val[(df_val["ev_away"] >= threshold) & df_val["market_away_moneyline"].apply(odds_in_range)].copy()
        bet_away["won"] = bet_away["home_won"] == 0
        bet_away["profit"] = bet_away.apply(lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1)

        all_bets = pd.concat([bet_home, bet_away])
        if len(all_bets) < 10:
            print(f"  EV>={threshold}: only {len(all_bets)} bets, too few")
            continue

        roi = all_bets["profit"].sum() / (len(all_bets) * STAKE) * 100
        win_rate = all_bets["won"].mean() * 100
        avg_odds = pd.concat([bet_home["market_home_moneyline"], bet_away["market_away_moneyline"]]).mean()
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"  EV>={threshold}: {len(all_bets)} bets, {win_rate:.1f}% win, avg odds {avg_odds:+.0f}, "
              f"${all_bets['profit'].sum():+.0f} profit, ROI={roi:+.1f}%{marker}")


if __name__ == "__main__":
    run()