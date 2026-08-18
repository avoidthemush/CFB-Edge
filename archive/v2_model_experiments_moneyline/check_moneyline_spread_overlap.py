"""
Tests whether games flagged by BOTH approved systems - Mid-Season Dog
(Spread) and Unranked Favorite Dog (Moneyline) - show stronger ML ROI
than Unranked Favorite Dog picks alone. Not a new signal - checking
convergence between two systems already independently validated,
using the actual saved Spread production model.
"""
import json
import joblib
import pandas as pd

STAKE = 100
GENERAL_CONFIDENCE_THRESHOLD = 0.60
FOCUSED_MIN_WEEK = 5


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


model = joblib.load("spread_production_model.joblib")
scaler = joblib.load("spread_production_scaler.joblib")
imputer = joblib.load("spread_production_imputer.joblib")
with open("spread_production_features.json") as f:
    feature_cols = json.load(f)

full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
full_df = full_df[full_df["season"] >= 2021].copy()
full_df = full_df[
    full_df["market_spread_open"].notna() & full_df["actual_spread"].notna() &
    full_df["market_home_moneyline"].notna() & full_df["market_away_moneyline"].notna()
]
full_df = full_df[full_df["market_spread_open"] != 0]

bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
for col in bool_cols:
    if col in full_df.columns:
        full_df[col] = full_df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

X = full_df[feature_cols]
X_imputed = imputer.transform(X)
X_scaled = scaler.transform(X_imputed)
probs = model.predict_proba(X_scaled)[:, 1]

full_df["prob_home_covers"] = probs
full_df["bet_on_home"] = full_df["prob_home_covers"] >= 0.5
full_df["spread_confidence"] = full_df["prob_home_covers"].where(full_df["bet_on_home"], 1 - full_df["prob_home_covers"])
full_df["is_underdog_bet"] = (
    (full_df["bet_on_home"] & (full_df["market_spread_open"] > 0)) |
    (~full_df["bet_on_home"] & (full_df["market_spread_open"] < 0))
)
full_df["mid_season_dog_fires"] = (
    (full_df["spread_confidence"] >= GENERAL_CONFIDENCE_THRESHOLD) &
    (full_df["week"] >= FOCUSED_MIN_WEEK) & full_df["is_underdog_bet"] & (full_df["neutral_site"] != True)
)

full_df["home_is_dog"] = full_df["market_spread_open"] > 0
full_df["dog_spread_size"] = full_df["market_spread_open"].abs()
full_df["dog_ml"] = full_df.apply(lambda r: r["market_home_moneyline"] if r["home_is_dog"] else r["market_away_moneyline"], axis=1)
full_df["dog_won"] = full_df.apply(lambda r: (r["actual_spread"] > 0) if r["home_is_dog"] else (r["actual_spread"] < 0), axis=1)
full_df["favorite_is_ranked"] = full_df.apply(lambda r: r["away_is_ranked"] if r["home_is_dog"] else r["home_is_ranked"], axis=1)
full_df["unranked_dog_fires"] = (full_df["dog_spread_size"] <= 10) & (full_df["favorite_is_ranked"] == 0)

ml_pool = full_df[full_df["unranked_dog_fires"]].copy()
overlap = ml_pool[ml_pool["mid_season_dog_fires"]].copy()
no_overlap = ml_pool[~ml_pool["mid_season_dog_fires"]].copy()

for label, subset in [("OVERLAP (both systems agree)", overlap), ("NO OVERLAP (ML dog fires alone)", no_overlap)]:
    if len(subset) == 0:
        print(f"{label}: no bets")
        continue
    subset = subset.copy()
    subset["profit"] = subset.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
    win_rate = subset["dog_won"].mean() * 100
    profit = subset["profit"].sum()
    roi = profit / (len(subset) * STAKE) * 100
    marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
    print(f"\n{label}: n={len(subset)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}")
    for year in sorted(subset["season"].unique()):
        year_df = subset[subset["season"] == year]
        if len(year_df) < 5:
            continue
        yroi = year_df["profit"].sum() / (len(year_df) * STAKE) * 100
        print(f"    {year}: n={len(year_df)}, ROI={yroi:+.1f}%")