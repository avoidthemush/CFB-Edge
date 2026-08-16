"""
Check 3: builds TWO genuinely different model types (logistic
regression, gradient-boosted trees) on the same 'without recruiting'
feature set, and checks whether requiring BOTH to agree produces a
stronger, more reliable signal than either alone.
"""
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

NON_FEATURE_COLUMNS = [
    "game_id", "season", "week", "market_provider",
    "actual_spread", "actual_total", "home_won",
]
MARKET_COLUMNS = [
    "market_spread", "market_spread_open", "market_total", "market_total_open",
    "market_home_moneyline", "market_away_moneyline",
]
ID_COLUMNS = ["home_coach_id", "away_coach_id"]
RECRUITING_COLS = [
    "home_recruiting_rank", "away_recruiting_rank", "diff_recruiting_rank",
    "home_recruiting_points", "away_recruiting_points", "diff_recruiting_points",
    "home_off_new_talent_impact", "away_off_new_talent_impact", "diff_off_new_talent_impact",
    "home_def_new_talent_impact", "away_def_new_talent_impact", "diff_def_new_talent_impact",
    "talent_edge_early_season", "recruiting_edge_early_season",
]

TREE_PARAMS = dict(
    n_estimators=200, max_depth=3, learning_rate=0.02,
    subsample=0.7, colsample_bytree=0.6,
    reg_alpha=0.5, reg_lambda=2.0, min_child_weight=5,
)

CONFIDENCE_THRESHOLD = 0.58  # slightly lower since agreement itself is the filter
FOLDS = [
    (2015, 2021, 2022),
    (2015, 2022, 2023),
    (2015, 2023, 2024),
    (2015, 2024, 2025),
]


def prepare(df, exclude_cols):
    df = df[df["market_spread_open"].notna() & df["actual_spread"].notna()].copy()
    df["open_implied_margin"] = -df["market_spread_open"]
    df["margin_vs_open"] = df["actual_spread"] - df["open_implied_margin"]
    df = df[df["margin_vs_open"] != 0]
    df["home_covers"] = (df["margin_vs_open"] > 0).astype(int)

    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": 1, "False": 0, True: 1, False: 0}).astype("Int64")

    base_exclude = NON_FEATURE_COLUMNS + MARKET_COLUMNS + ID_COLUMNS + exclude_cols + \
                   ["open_implied_margin", "margin_vs_open", "home_covers"]
    feature_cols = [c for c in df.columns if c not in base_exclude]
    return df, df[feature_cols], df["home_covers"], feature_cols


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)

    exclude = [c for c in RECRUITING_COLS if c in full_df.columns]

    logreg_only_results = []
    tree_only_results = []
    agreement_results = []

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude)
        df_test, X_test, y_test, _ = prepare(test_df, exclude)

        if len(df_train) < 100 or len(df_test) < 30:
            continue

        # Logistic regression
        imputer = SimpleImputer(strategy="median")
        X_train_imputed = imputer.fit_transform(X_train)
        X_test_imputed = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imputed)
        X_test_scaled = scaler.transform(X_test_imputed)

        logreg = LogisticRegression(max_iter=2000, C=0.1, random_state=42)
        logreg.fit(X_train_scaled, y_train)
        logreg_probs = logreg.predict_proba(X_test_scaled)[:, 1]

        # Gradient-boosted trees
        tree = xgb.XGBClassifier(random_state=42, eval_metric="logloss", **TREE_PARAMS)
        tree.fit(X_train, y_train)
        tree_probs = tree.predict_proba(X_test)[:, 1]

        logreg_home = logreg_probs >= CONFIDENCE_THRESHOLD
        logreg_away = logreg_probs <= (1 - CONFIDENCE_THRESHOLD)
        logreg_bet = logreg_home | logreg_away

        tree_home = tree_probs >= CONFIDENCE_THRESHOLD
        tree_away = tree_probs <= (1 - CONFIDENCE_THRESHOLD)
        tree_bet = tree_home | tree_away

        # Agreement: both models want to bet, AND on the same side
        both_bet = logreg_bet & tree_bet
        same_side = (logreg_home == tree_home)
        agree_mask = both_bet & same_side

        actual_home_covers = y_test.values.astype(bool)

        def score(mask, predicted_home):
            if mask.sum() == 0:
                return None, 0
            correct = predicted_home[mask] == actual_home_covers[mask]
            return correct.mean() * 100, mask.sum()

        lr_rate, lr_n = score(logreg_bet, logreg_home)
        tree_rate, tree_n = score(tree_bet, tree_home)
        agree_rate, agree_n = score(agree_mask, logreg_home)

        print(f"\n=== {test_year} ===")
        print(f"  Logistic regression alone: {lr_n} bets, {lr_rate:.1f}% win rate" if lr_rate else "  Logistic regression alone: no bets")
        print(f"  Trees alone:               {tree_n} bets, {tree_rate:.1f}% win rate" if tree_rate else "  Trees alone: no bets")
        print(f"  BOTH AGREE:                {agree_n} bets, {agree_rate:.1f}% win rate" if agree_rate else "  Both agree: no bets")

        if lr_rate: logreg_only_results.append((test_year, lr_rate, lr_n))
        if tree_rate: tree_only_results.append((test_year, tree_rate, tree_n))
        if agree_rate: agreement_results.append((test_year, agree_rate, agree_n))

    def summarize(label, results):
        if not results:
            print(f"\n{label}: no results")
            return
        avg = sum(r for _, r, _ in results) / len(results)
        above = sum(1 for _, r, _ in results if r >= 52.4)
        total_n = sum(n for _, _, n in results)
        print(f"\n{label}: AVG {avg:.1f}% | {above}/{len(results)} years above breakeven | {total_n} total bets")

    print("\n\n=== SUMMARY ===")
    summarize("Logistic regression alone", logreg_only_results)
    summarize("Trees alone", tree_only_results)
    summarize("BOTH MODELS AGREE", agreement_results)


if __name__ == "__main__":
    run()