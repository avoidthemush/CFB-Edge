"""
Diagnoses why EV-based betting performed WORSE than edge-gap betting.
Theory: EV = prob x payout, and payout multipliers are large for
underdogs, so small probability errors get amplified into
misleadingly-large apparent EV specifically on longshots. Checking the
actual composition of EV-qualifying bets to confirm.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

FEATURE_PATTERNS = [
    "returning_qb1", "returning_ppa_pct", "returning_havoc_pct",
    "off_success_rate", "off_explosiveness", "def_havoc_rate",
    "def_points_per_opportunity", "def_success_rate_allowed",
    "off_line_yards", "off_power_success", "def_stuff_rate",
    "off_ppa", "def_ppa",
]
NON_FEATURE_COLUMNS = ["game_id", "season", "week", "market_provider", "actual_spread", "actual_total", "home_won"]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]


def payout_per_dollar(odds):
    if odds > 0:
        return odds / 100
    return 100 / -odds


def expected_value(our_prob, odds):
    payout = payout_per_dollar(odds)
    return our_prob * payout - (1 - our_prob)


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
df_val["ev_home"] = df_val.apply(lambda r: expected_value(r["our_home_prob"], r["market_home_moneyline"]), axis=1)
df_val["ev_away"] = df_val.apply(lambda r: expected_value(1 - r["our_home_prob"], r["market_away_moneyline"]), axis=1)

qualifying_home = df_val[df_val["ev_home"] >= 0.05]
qualifying_away = df_val[df_val["ev_away"] >= 0.05]

print(f"EV>=0.05 bets: {len(qualifying_home)} home, {len(qualifying_away)} away\n")
print(f"Home-side qualifying bets - avg market odds: {qualifying_home['market_home_moneyline'].mean():+.0f}")
print(f"Away-side qualifying bets - avg market odds: {qualifying_away['market_away_moneyline'].mean():+.0f}")
print(f"\nAll games (for comparison) - avg home odds: {df_val['market_home_moneyline'].mean():+.0f}, "
      f"avg away odds: {df_val['market_away_moneyline'].mean():+.0f}")

print(f"\n% of qualifying bets that are underdogs (positive odds):")
print(f"  Home qualifying: {(qualifying_home['market_home_moneyline'] > 0).mean()*100:.1f}%")
print(f"  Away qualifying: {(qualifying_away['market_away_moneyline'] > 0).mean()*100:.1f}%")