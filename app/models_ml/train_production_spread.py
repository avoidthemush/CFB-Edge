"""
Trains and SAVES the actual production Spread model - the real thing
that generates live picks, as distinct from every validation/walk-forward
script that only ever trained temporary in-memory models to measure
performance. Per V2_MODEL_PLAN.md naming convention: this is the
validation model becoming the production model.

Trained on ALL available data (2015-2025) - no held-out test year, since
2015-2024 was training and 2025 was the sealed validation holdout, both
now folded in. Real 2026 games are the true test, going forward live.

Uses the LOCKED "Mid-Season Value Dog" system configuration: recruiting/
talent-impact columns excluded (ablation-confirmed to hurt), everything
else included (matchups, coach quality/h2h/upgrade, returning QB,
weather, market). The betting RULE (week>=5, underdog-only, confidence
>=0.60, non-neutral-site) is applied downstream at prediction time, not
baked into training - this script just trains the underlying classifier.
"""
import json
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]
RECRUITING_COLS = [
    "home_recruiting_rank", "away_recruiting_rank", "diff_recruiting_rank",
    "home_recruiting_points", "away_recruiting_points", "diff_recruiting_points",
    "home_off_new_talent_impact", "away_off_new_talent_impact", "diff_off_new_talent_impact",
    "home_def_new_talent_impact", "away_def_new_talent_impact", "diff_def_new_talent_impact",
    "talent_edge_early_season", "recruiting_edge_early_season",
]

MODEL_PARAMS = dict(max_iter=2000, C=0.1, random_state=42)


def prepare(df):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]  # drop pushes - no decision to learn from
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    exclude = NON_FEATURE_COLUMNS + ID_COLUMNS + RECRUITING_COLS + \
              ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in df.columns if c not in exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def train_production_model():
    print("Loading ALL available data (2015-2025, training + sealed holdout combined)...")
    df_train_years = pd.read_csv("training_data_validation_v2_fbs.csv")
    df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([df_train_years, df_2025], ignore_index=True)

    df, X, y, feature_cols = prepare(full_df)
    print(f"Training on {len(X)} games, {len(feature_cols)} features")

    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    model = LogisticRegression(**MODEL_PARAMS)
    model.fit(X_scaled, y)

    train_acc = model.score(X_scaled, y)
    print(f"Fit-on-everything accuracy (NOT a real performance measure - no held-out "
          f"test here, that's what walk-forward validation already did): {train_acc*100:.1f}%")

    joblib.dump(model, "spread_production_model.joblib")
    joblib.dump(scaler, "spread_production_scaler.joblib")
    joblib.dump(imputer, "spread_production_imputer.joblib")

    with open("spread_production_features.json", "w") as f:
        json.dump(feature_cols, f, indent=2)

    print(f"\nSaved: spread_production_model.joblib, spread_production_scaler.joblib, "
          f"spread_production_imputer.joblib, spread_production_features.json "
          f"({len(feature_cols)} feature names, in order)")
    print(f"\nThis is the REAL model, used by predict_week.py for live picks.")
    print(f"System: Mid-Season Value Dog (week>=5, underdog-only, confidence>=0.60, "
          f"non-neutral-site). Historical validated performance: 58.7% win rate on 407 "
          f"bets across 4 independent walk-forward test years. See V2_MODEL_PLAN.md.")


if __name__ == "__main__":
    train_production_model()