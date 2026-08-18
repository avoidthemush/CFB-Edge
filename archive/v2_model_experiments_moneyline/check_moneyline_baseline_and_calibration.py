"""
Diagnoses the puzzling pattern: strong overall accuracy (68.1%) but
losing money at every edge threshold except the highest. Checks (1) a
naive 'always bet the market's own favorite' baseline for comparison,
and (2) whether our classifier's probabilities are actually calibrated.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from app.models_ml.moneyline.devig import devig_two_way

STAKE = 100
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


def prepare(df, all_columns):
    df = df[df["market_home_moneyline"].notna() & df["market_away_moneyline"].notna() & df["actual_spread"].notna()].copy()
    df["home_won"] = (df["actual_spread"] > 0).astype(int)
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in all_columns if any(p in c for p in FEATURE_PATTERNS) and c not in NON_FEATURE_COLUMNS + ID_COLUMNS]
    return df, df[feature_cols], df["home_won"], feature_cols


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
df_val["actual_home_won"] = y_val.values.astype(bool)

print("=== BASELINE: always bet the market's own favorite ===")
df_val["market_favors_home"] = df_val["market_home_moneyline"] < 0
bet_odds = df_val.apply(lambda r: r["market_home_moneyline"] if r["market_favors_home"] else r["market_away_moneyline"], axis=1)
won = df_val.apply(lambda r: r["actual_home_won"] if r["market_favors_home"] else not r["actual_home_won"], axis=1)
profit = pd.Series([american_odds_profit(o, w) for o, w in zip(bet_odds, won)])
print(f"  {len(df_val)} bets, {won.mean()*100:.1f}% win, ${profit.sum():+.0f} profit, ROI={profit.sum()/(len(df_val)*STAKE)*100:+.1f}%")

print("\n=== CALIBRATION: our predicted probability vs actual win rate ===")
buckets = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]
for low, high in buckets:
    bucket = df_val[(df_val["our_home_prob"] >= low) & (df_val["our_home_prob"] < high)]
    if len(bucket) == 0:
        continue
    actual_rate = bucket["actual_home_won"].mean() * 100
    print(f"  Predicted {low*100:.0f}-{high*100:.0f}%: n={len(bucket)}, actual win rate={actual_rate:.1f}%")

for low, high in buckets:
    bucket = df_val[(df_val["our_home_prob"] <= 1-low) & (df_val["our_home_prob"] > 1-high)]
    if len(bucket) == 0:
        continue
    actual_rate = (~bucket["actual_home_won"]).mean() * 100
    print(f"  Predicted AWAY {low*100:.0f}-{high*100:.0f}%: n={len(bucket)}, actual win rate={actual_rate:.1f}%")