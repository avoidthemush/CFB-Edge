"""
Recomputes sign-flip rate scoped to market-line games only (the games
that actually matter for betting relevance) - the original robustness
check mixed in low-info, non-market blowout games that inflate the
sign-flip count without reflecting real prediction failures.
"""
import pandas as pd
import xgboost as xgb

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
TARGET_COLUMN = "actual_spread"


def load_and_prepare(path):
    df = pd.read_csv(path)
    df = df[df[TARGET_COLUMN].notna()].copy()
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return df, df[feature_cols], df[TARGET_COLUMN], feature_cols


df_train, X_train, y_train, feature_cols = load_and_prepare("training_data_validation.csv")
df_test, X_test, y_test, _ = load_and_prepare("training_data_2025_holdout.csv")

model = xgb.XGBRegressor(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, random_state=42,
)
model.fit(X_train, y_train)
preds = model.predict(X_test)

market_mask = df_test["market_spread"].notna()

print(f"Total holdout games: {len(y_test)}")
print(f"Games WITH a market line: {market_mask.sum()}")

# Sign flip, ALL games (the original, misleading number)
all_flips = ((y_test > 0) != (preds > 0)).sum()
print(f"\nSign-flip rate, ALL games: {all_flips/len(y_test)*100:.1f}% ({all_flips}/{len(y_test)})")

# Sign flip, market-line games only (the real number that matters)
y_market = y_test[market_mask]
preds_market = preds[market_mask]
market_flips = ((y_market > 0) != (preds_market > 0)).sum()
print(f"Sign-flip rate, MARKET-LINE games only: {market_flips/len(y_market)*100:.1f}% ({market_flips}/{len(y_market)})")

# Further scoped: close games specifically (|actual| <= 10) - where a sign flip is most costly
close_mask = market_mask & (y_test.abs() <= 10)
y_close = y_test[close_mask]
preds_close = preds[close_mask]
close_flips = ((y_close > 0) != (preds_close > 0)).sum()
print(f"Sign-flip rate, CLOSE market games (|actual|<=10): {close_flips/len(y_close)*100:.1f}% ({close_flips}/{len(y_close)})")