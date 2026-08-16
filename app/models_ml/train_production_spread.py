"""
Trains and SAVES the actual production Spread model - General Model
system (returning_qb + returning_production + raw_offense_defense_stats,
confidence>=0.60, no situational restrictions). This is the base model
that predict_week.py runs on every game; Focused Value is derived from
the SAME trained model with additional situational filters applied at
prediction time, not a separately trained model.

Trained on ALL available data (2021-2025, the real usable window given
market_spread_open coverage - see DESIGN_DECISIONS.md). 2015-2020
excluded: confirmed 0% open-line coverage, contributes no signal to
anything requiring an opening line.
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

GENERAL_MODEL_PATTERNS = {
    "returning_qb": ["returning_qb1"],
    "returning_production": ["returning_ppa_pct", "returning_havoc_pct"],
    "raw_offense_defense_stats": ["off_success_rate", "off_explosiveness", "def_havoc_rate",
                                    "def_points_per_opportunity", "def_success_rate_allowed",
                                    "off_line_yards", "off_power_success", "def_stuff_rate",
                                    "off_ppa", "def_ppa"],
}

MODEL_PARAMS = dict(C=0.1, max_iter=2000, random_state=42)


def get_cols_for_patterns(all_columns, patterns):
    return [c for c in all_columns if any(p in c for p in patterns)]


def prepare(df, all_columns):
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
    for patterns in GENERAL_MODEL_PATTERNS.values():
        keep.update(get_cols_for_patterns(all_columns, patterns))

    exclude_always = NON_FEATURE_COLUMNS + ID_COLUMNS + \
                      ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in keep if c in df.columns and c not in exclude_always]
    return df, df[feature_cols], df["home_covers"], feature_cols


def train_production_model():
    print("Loading ALL usable data (2021-2025 - real window given market_spread_open coverage)...")
    df_train_years = pd.read_csv("training_data_validation_v2_fbs.csv")
    df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([df_train_years, df_2025], ignore_index=True)
    full_df = full_df[full_df["season"] >= 2021]

    all_columns = full_df.columns.tolist()
    df, X, y, feature_cols = prepare(full_df, all_columns)
    print(f"Training on {len(X)} games, {len(feature_cols)} features (General Model config)")

    imputer = SimpleImputer(strategy="median")
    X_imputed = imputer.fit_transform(X)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    model = LogisticRegression(**MODEL_PARAMS)
    model.fit(X_scaled, y)

    train_acc = model.score(X_scaled, y)
    print(f"Fit-on-everything accuracy (NOT a real performance measure - see walk-forward "
          f"results in SPREAD_FEATURE_LOG.md): {train_acc*100:.1f}%")

    joblib.dump(model, "spread_production_model.joblib")
    joblib.dump(scaler, "spread_production_scaler.joblib")
    joblib.dump(imputer, "spread_production_imputer.joblib")

    with open("spread_production_features.json", "w") as f:
        json.dump(feature_cols, f, indent=2)

    print(f"\nSaved: spread_production_model.joblib, spread_production_scaler.joblib, "
          f"spread_production_imputer.joblib, spread_production_features.json "
          f"({len(feature_cols)} feature names, in order)")
    print(f"\nThis model powers BOTH approved systems (predict_week.py applies each system's")
    print(f"own rules on top of the same underlying prediction):")
    print(f"  General Model: confidence>=0.60, no restrictions - 55.3% pooled walk-forward")
    print(f"  Focused Value: + week>=5, underdog-only, non-neutral - 60.8% pooled walk-forward")
    print(f"See SPREAD_FEATURE_LOG.md for full validation history.")


if __name__ == "__main__":
    train_production_model()