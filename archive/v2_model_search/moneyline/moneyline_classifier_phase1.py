"""
Type A for Moneyline: direct "home_won" classifier, reusing the proven
feature categories from Spread's General Model (returning_qb,
returning_production, raw_offense_defense_stats) - a genuinely related
question (who wins vs who covers), not built from scratch.

Edge = our probability - devigged market probability. Bet only when
edge exceeds a threshold. Evaluated via REAL ROI on actual American
odds, not win rate - the lesson already paid for twice tonight.

Phase 1: train 2021-2023, validate 2024. 2025 held back.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from app.models_ml.moneyline.devig import devig_two_way

STAKE = 100
EDGE_THRESHOLDS = [0.03, 0.05, 0.07, 0.10, 0.15]

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


def get_feature_cols(all_columns):
    return [c for c in all_columns if any(p in c for p in FEATURE_PATTERNS)]


def prepare(df, all_columns):
    df = df[
        df["market_home_moneyline"].notna() & df["market_away_moneyline"].notna() &
        df["actual_spread"].notna()
    ].copy()
    df["home_won"] = (df["actual_spread"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    feature_cols = get_feature_cols(all_columns)
    exclude = NON_FEATURE_COLUMNS + ID_COLUMNS
    feature_cols = [c for c in feature_cols if c not in exclude]
    return df, df[feature_cols], df["home_won"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]
    all_columns = full_df.columns.tolist()

    train_df = full_df[(full_df["season"] >= 2021) & (full_df["season"] <= 2023)]
    val_df = full_df[full_df["season"] == 2024]

    df_train, X_train, y_train, feature_cols = prepare(train_df, all_columns)
    df_val, X_val, y_val, _ = prepare(val_df, all_columns)

    print(f"Train: {len(X_train)} games | Validate: {len(X_val)} games | Features: {len(feature_cols)}\n")

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

    devig_results = df_val.apply(
        lambda row: devig_two_way(row["market_home_moneyline"], row["market_away_moneyline"]), axis=1
    )
    df_val["market_fair_home_prob"] = devig_results.apply(lambda x: x[0])
    df_val["edge"] = df_val["our_home_prob"] - df_val["market_fair_home_prob"]
    df_val = df_val.dropna(subset=["edge"])

    overall_acc = ((probs >= 0.5).astype(int) == y_val.values).mean() * 100
    print(f"Overall classifier accuracy (all games, not just edge bets): {overall_acc:.1f}%\n")

    print("=== Results by edge threshold ===")
    for threshold in EDGE_THRESHOLDS:
        bet_home = df_val[df_val["edge"] >= threshold].copy()
        bet_home["won"] = bet_home["home_won"] == 1
        bet_home["profit"] = bet_home.apply(lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1)

        bet_away = df_val[df_val["edge"] <= -threshold].copy()
        bet_away["won"] = bet_away["home_won"] == 0
        bet_away["profit"] = bet_away.apply(lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1)

        all_bets = pd.concat([bet_home, bet_away])
        if len(all_bets) < 10:
            print(f"  edge>={threshold}: only {len(all_bets)} bets, too few")
            continue

        roi = all_bets["profit"].sum() / (len(all_bets) * STAKE) * 100
        win_rate = all_bets["won"].mean() * 100
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"  edge>={threshold}: {len(all_bets)} bets, {win_rate:.1f}% win, "
              f"${all_bets['profit'].sum():+.0f} profit, ROI={roi:+.1f}%{marker}")


if __name__ == "__main__":
    run()