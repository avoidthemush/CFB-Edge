"""
Mathematically principled reframing: Total = home_points + away_points
is an EXACT identity, not something to approximate with one blended
model. Predicts each side's points SEPARATELY (home offense vs away
defense matchup, and vice versa), then sums the two predictions.
Respects the real asymmetric structure of the problem instead of
blending both teams into one combined feature set.

Also includes an explicit pace x efficiency INTERACTION TERM - a linear
model cannot discover multiplicative relationships from additive inputs
alone; if pace and efficiency truly interact, we have to build that
ourselves.

Phase 1 only: train 2021-2023/validate 2024, plus train 2021-2022/
validate 2023. 2025 still reserved.
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


def _team_side_features(df, side):
    """side = 'home' or 'away'. Builds that team's own scoring-side features."""
    opp = "away" if side == "home" else "home"

    pass_matchup = df[f"matchup_{side}_pass_off_vs_{opp}_pass_def"]
    rush_matchup = df[f"matchup_{side}_rush_off_vs_{opp}_rush_def"]
    run_block_matchup = df[f"matchup_{side}_run_block_vs_{opp}_run_stop"]
    power_matchup = df[f"matchup_{side}_power_vs_{opp}_stuff"]

    pace = df[f"{side}_off_plays_per_drive"]
    third_down = df[f"{side}_off_third_down_pct"]
    field_position = df[f"{side}_off_field_position_predicted_points"]

    # Explicit interaction term - pace x matchup scoring potential.
    # A linear model can't discover this multiplicatively on its own.
    scoring_potential = pass_matchup + rush_matchup
    pace_x_efficiency = pace * scoring_potential

    return pd.DataFrame({
        f"{side}_pass_matchup": pass_matchup,
        f"{side}_rush_matchup": rush_matchup,
        f"{side}_run_block_matchup": run_block_matchup,
        f"{side}_power_matchup": power_matchup,
        f"{side}_pace": pace,
        f"{side}_third_down": third_down,
        f"{side}_field_position": field_position,
        f"{side}_pace_x_efficiency": pace_x_efficiency,
    })


def prepare(df, side, target_col):
    df = df[df["market_total_open"].notna() & df["actual_total"].notna() & df[target_col].notna()].copy()
    df["is_dome"] = df["is_dome"].map({"True": 1, "False": 0, True: 1, False: 0})

    side_features = _team_side_features(df, side)
    shared = df[["temp_f", "wind_mph", "precip_prob", "wind_x_pass_rate", "is_dome"]]

    X = pd.concat([side_features, shared], axis=1)
    y = df[target_col]

    return df, X, y, X.columns.tolist()


def train_side_model(train_df, side, target_col):
    _, X_train, y_train, feature_cols = prepare(train_df, side, target_col)
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)

    model = Ridge(alpha=10.0, random_state=42)
    model.fit(X_train_scaled, y_train)
    return model, imputer, scaler, feature_cols


def predict_side(model, imputer, scaler, val_df, side, target_col):
    df_val, X_val, y_val, feature_cols = prepare(val_df, side, target_col)
    X_val_imp = imputer.transform(X_val)
    X_val_scaled = scaler.transform(X_val_imp)
    preds = model.predict(X_val_scaled)
    return df_val, preds, y_val


def evaluate(full_df, train_start, train_end, val_year):
    train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
    val_df = full_df[full_df["season"] == val_year]

    home_model, home_imp, home_scaler, home_feats = train_side_model(train_df, "home", "home_points")
    away_model, away_imp, away_scaler, away_feats = train_side_model(train_df, "away", "away_points")

    # Need home_points/away_points columns - reconstruct from actual_spread/actual_total
    # since our CSVs store spread/total, not raw scores directly
    for d in [train_df, val_df]:
        pass  # handled below via full_df prep

    df_home_val, home_preds, home_actual = predict_side(home_model, home_imp, home_scaler, val_df, "home", "home_points")
    df_away_val, away_preds, away_actual = predict_side(away_model, away_imp, away_scaler, val_df, "away", "away_points")

    home_mae = mean_absolute_error(home_actual, home_preds)
    away_mae = mean_absolute_error(away_actual, away_preds)

    df_val = df_home_val.copy()
    df_val["predicted_total"] = home_preds + away_preds
    df_val["gap"] = df_val["predicted_total"] - df_val["market_total_open"]
    df_val["bet_over"] = df_val["gap"] > 0
    df_val["actual_over"] = df_val["actual_total"] > df_val["market_total_open"]
    df_val = df_val[df_val["actual_total"] != df_val["market_total_open"]]

    return df_val, home_mae, away_mae


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024].copy()

    # Reconstruct raw scores from spread/total (home+away=total, home-away=spread)
    full_df["home_points"] = (full_df["actual_total"] + full_df["actual_spread"]) / 2
    full_df["away_points"] = (full_df["actual_total"] - full_df["actual_spread"]) / 2

    for label, start, end, val in SPLITS:
        df_val, home_mae, away_mae = evaluate(full_df, start, end, val)
        print(f"\n=== {label} ===")
        print(f"  Home-side MAE: {home_mae:.2f} | Away-side MAE: {away_mae:.2f}")

        for threshold in GAP_THRESHOLDS:
            confident = df_val[df_val["gap"].abs() >= threshold]
            if len(confident) == 0:
                print(f"  Gap>={threshold}: no bets")
                continue
            correct = confident["bet_over"] == confident["actual_over"]
            win_rate = correct.mean() * 100
            marker = " <-- above breakeven" if win_rate >= 52.4 else ""
            print(f"  Gap>={threshold}: {len(confident)} bets, {win_rate:.1f}% win rate{marker}")


if __name__ == "__main__":
    run()