"""
Redesigned Total approach: uses EXISTING matchup features (built for
Spread, never applied to Total) instead of raw additive stats. Each
side's scoring potential is opponent-adjusted (offense vs THIS specific
defense), not just "how good is this offense in general" - directly
addresses the "great offense vs stout defense should be suppressed"
gap in the earlier purely-additive approach.

Zero regeneration needed - matchup_* columns already exist in current
data. Same Phase 1 discipline (train 2021-2023, validate 2024, second
split validating 2023), 2025 still reserved.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error

SPLITS = [
    ("train 2021-2023, validate 2024", 2021, 2023, 2024),
    ("train 2021-2022, validate 2023", 2021, 2022, 2023),
]
GAP_THRESHOLDS = [2, 3, 5, 7]


def prepare(df):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})

    # Opponent-adjusted scoring potential - each side's matchup edges summed
    df["home_matchup_scoring_potential"] = (
        df["matchup_home_pass_off_vs_away_pass_def"] + df["matchup_home_rush_off_vs_away_rush_def"]
    )
    df["away_matchup_scoring_potential"] = (
        df["matchup_away_pass_off_vs_home_pass_def"] + df["matchup_away_rush_off_vs_home_rush_def"]
    )
    df["combined_matchup_scoring_potential"] = (
        df["home_matchup_scoring_potential"] + df["away_matchup_scoring_potential"]
    )

    # Trenches matchups, same logic
    df["combined_trenches_potential"] = (
        df["matchup_home_run_block_vs_away_run_stop"] + df["matchup_away_run_block_vs_home_run_stop"] +
        df["matchup_home_power_vs_away_stuff"] + df["matchup_away_power_vs_home_stuff"]
    )

    # Pace still matters as a multiplier context, kept as combined (this
    # part genuinely IS additive - more plays for BOTH teams raises total
    # regardless of who's more efficient)
    df["combined_pace"] = df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"]

    # Ability to sustain drives (third down) - also genuinely additive,
    # more conversions by either team = more plays = more scoring chances
    df["combined_off_third_down_pct"] = df["home_off_third_down_pct"] + df["away_off_third_down_pct"]

    feature_cols = [
        "combined_matchup_scoring_potential", "home_matchup_scoring_potential",
        "away_matchup_scoring_potential", "combined_trenches_potential",
        "combined_pace", "combined_off_third_down_pct",
        "temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome",
    ]

    return df, df[feature_cols], df["actual_total"], feature_cols


def evaluate(full_df, train_start, train_end, val_year):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    val_df = full_df[full_df["season"] == val_year]

    df_train, X_train, y_train, feature_cols = prepare(train_df)
    df_val, X_val, y_val, _ = prepare(val_df)

    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_val_imp = imputer.transform(X_val)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_val_scaled = scaler.transform(X_val_imp)

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train)

    train_preds = model.predict(X_train_scaled)
    val_preds = model.predict(X_val_scaled)
    train_mae = mean_absolute_error(y_train, train_preds)
    val_mae = mean_absolute_error(y_val, val_preds)

    df_val = df_val.copy()
    df_val["predicted_total"] = val_preds
    df_val["gap"] = df_val["predicted_total"] - df_val["market_total_open"]
    df_val["bet_over"] = df_val["gap"] > 0
    df_val["actual_over"] = df_val["actual_total"] > df_val["market_total_open"]
    df_val = df_val[df_val["actual_total"] != df_val["market_total_open"]]

    return df_val, train_mae, val_mae, feature_cols, model


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    for label, start, end, val in SPLITS:
        df_val, train_mae, val_mae, feature_cols, model = evaluate(full_df, start, end, val)
        gap = val_mae - train_mae
        print(f"\n=== {label} ===")
        print(f"  Train MAE: {train_mae:.2f} | Val MAE: {val_mae:.2f} | Gap: {gap:.2f}")

        for threshold in GAP_THRESHOLDS:
            confident = df_val[df_val["gap"].abs() >= threshold]
            if len(confident) == 0:
                print(f"  Gap>={threshold}: no bets")
                continue
            correct = confident["bet_over"] == confident["actual_over"]
            win_rate = correct.mean() * 100
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {len(confident)} bets, {win_rate:.1f}% win rate{marker}")

    df_val, _, _, feature_cols, model = evaluate(full_df, 2021, 2023, 2024)
    print("\n=== Feature coefficients (primary split) ===")
    coefs = pd.Series(model.coef_, index=feature_cols).sort_values(key=abs, ascending=False)
    for feat, coef in coefs.items():
        direction = "-> favors OVER" if coef > 0 else "-> favors UNDER"
        print(f"  {feat}: {coef:+.3f} {direction}")


if __name__ == "__main__":
    run()