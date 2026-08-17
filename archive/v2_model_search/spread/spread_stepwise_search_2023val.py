"""
Robustness check on the stepwise search: identical algorithm, but
validating against 2023 instead of 2024, still fully inside Phase 1
(2025 never touched). If this converges to a meaningfully different
feature set than the 2024 version, that confirms the original result
was overfit to 2024's specific games rather than real signal.
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

SEED_PATTERNS = ["returning_qb1", "returning_ppa_pct", "returning_havoc_pct",
                  "off_success_rate", "off_explosiveness", "def_havoc_rate",
                  "def_points_per_opportunity", "def_success_rate_allowed",
                  "off_line_yards", "off_power_success", "def_stuff_rate",
                  "off_ppa", "def_ppa"]

TRAIN_START, TRAIN_END, VALIDATE_YEAR = 2021, 2022, 2023
CONFIDENCE_THRESHOLD = 0.60
MAX_FORWARD_ROUNDS = 25
BACKWARD_EVERY_N_ROUNDS = 3


def prepare(df, feature_cols):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    return df, df[feature_cols], df["home_covers"]


def evaluate(full_df, feature_cols):
    if full_df["season"].max() >= 2025:
        raise ValueError("Blocked: dataset contains 2025")
    if len(feature_cols) == 0:
        return None

    train_df = full_df[(full_df["season"] >= TRAIN_START) & (full_df["season"] <= TRAIN_END)]
    val_df = full_df[full_df["season"] == VALIDATE_YEAR]

    df_train, X_train, y_train = prepare(train_df, feature_cols)
    df_val, X_val, y_val = prepare(val_df, feature_cols)

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

    if bet_mask.sum() < 15:
        return None

    predicted_home_covers = confident_home[bet_mask]
    actual_home_covers = y_val.values[bet_mask]
    correct = predicted_home_covers == actual_home_covers.astype(bool)
    return correct.mean() * 100, bet_mask.sum()


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= VALIDATE_YEAR]

    non_feature = set(NON_FEATURE_COLUMNS + ID_COLUMNS +
                       ["market_spread_open", "market_spread", "market_total",
                        "market_total_open", "market_home_moneyline", "market_away_moneyline"])
    all_features = [c for c in full_df.columns if c not in non_feature]

    current_set = [c for c in all_features if any(p in c for p in SEED_PATTERNS)]
    remaining_pool = [c for c in all_features if c not in current_set]

    result = evaluate(full_df, current_set)
    current_score, current_n = result
    print(f"SEED (Candidate A, {len(current_set)} features): {current_score:.2f}% ({current_n} bets)\n")

    for round_num in range(1, MAX_FORWARD_ROUNDS + 1):
        print(f"--- Forward round {round_num} ---")
        best_addition = None
        best_score = current_score

        for candidate in remaining_pool:
            trial_set = current_set + [candidate]
            result = evaluate(full_df, trial_set)
            if result is None:
                continue
            score, n = result
            if score > best_score:
                best_score = score
                best_addition = candidate

        if best_addition is None:
            print("  Converged.\n")
            break

        current_set.append(best_addition)
        remaining_pool.remove(best_addition)
        current_score = best_score
        result = evaluate(full_df, current_set)
        _, current_n = result
        print(f"  ADDED: {best_addition} -> {current_score:.2f}% ({current_n} bets, {len(current_set)} features)\n")

        if round_num % BACKWARD_EVERY_N_ROUNDS == 0:
            print(f"--- Backward check (after round {round_num}) ---")
            improved = True
            while improved:
                improved = False
                for feat in list(current_set):
                    trial_set = [c for c in current_set if c != feat]
                    result = evaluate(full_df, trial_set)
                    if result is None:
                        continue
                    score, n = result
                    if score >= current_score:
                        print(f"  REMOVED: {feat} -> {score:.2f}% ({n} bets, {len(trial_set)} features)")
                        current_set.remove(feat)
                        remaining_pool.append(feat)
                        current_score = score
                        improved = True
                        break
            print()

    print("="*70)
    print(f"FINAL CONVERGED SET (validated on 2023): {len(current_set)} features, {current_score:.2f}%")
    print("="*70)
    for f in sorted(current_set):
        print(f"  {f}")

    print("\n=== Compare this list against the 2024-validated run's final set ===")
    print("Overlap in feature selection between the two runs = real evidence.")
    print("Wildly different selections = confirms overfitting to whichever year was used.")


if __name__ == "__main__":
    run()