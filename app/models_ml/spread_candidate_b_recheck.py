"""
Second-look robustness check on the strongest surviving candidate from
the variable-size search: returning_qb + returning_production +
coach_quality + weather + recent_form. Re-validates on 2023 (still
Phase 1, still not touching 2025) to see if this candidate holds up on
an independent year, same discipline applied to the stepwise search
results earlier tonight.
"""
import pandas as pd
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


def evaluate(full_df, all_columns, patterns_list, train_start, train_end, val_year):
    if full_df["season"].max() >= 2025:
        raise ValueError("Blocked: 2025 present")

    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    val_df = full_df[full_df["season"] == val_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df, patterns_list, all_columns)
    df_val, X_val, y_val, _ = prepare(val_df, patterns_list, all_columns)

    if len(df_train) < 100 or len(df_val) < 30:
        return None

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = LogisticRegression(C=0.1, max_iter=2000, random_state=42)
    model.fit(X_train_scaled, y_train)
    probs = model.predict_proba(X_val_scaled)[:, 1]

    confident_home = probs >= CONFIDENCE_THRESHOLD
    confident_away = probs <= (1 - CONFIDENCE_THRESHOLD)
    bet_mask = confident_home | confident_away
    if bet_mask.sum() == 0:
        return None

    predicted_home_covers = confident_home[bet_mask]
    actual_home_covers = y_val.values[bet_mask]
    correct = predicted_home_covers == actual_home_covers.astype(bool)
    return correct.mean() * 100, bet_mask.sum()


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]
    all_columns = full_df.columns.tolist()
    patterns_list = list(CANDIDATE_B_PATTERNS.values())

    print("Candidate B: returning_qb + returning_production + coach_quality + weather + recent_form\n")

    for label, start, end, val in [
        ("Original (train 2021-2023, validate 2024)", 2021, 2023, 2024),
        ("Recheck (train 2021-2022, validate 2023)", 2021, 2022, 2023),
    ]:
        result = evaluate(full_df, all_columns, patterns_list, start, end, val)
        if result:
            print(f"{label}: {result[0]:.2f}% ({result[1]} bets)")
        else:
            print(f"{label}: insufficient data")


if __name__ == "__main__":
    run()