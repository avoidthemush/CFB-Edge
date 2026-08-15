"""
Rigorously tests the "WITHOUT recruiting/talent-impact" config - the
best-looking result of the night - across ALL confidence thresholds
(not just 0.60) with statistical significance testing, same standard
applied to every other result tonight. A real edge should hold up
across nearby thresholds too, not just the one we happened to check.
"""
import pandas as pd
from scipy.stats import binomtest
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

CONFIDENCE_THRESHOLDS = [0.50, 0.55, 0.58, 0.60, 0.63, 0.65]
BREAKEVEN = 0.524
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

    pooled_by_threshold = {t: [0, 0] for t in CONFIDENCE_THRESHOLDS}
    year_results_by_threshold = {t: [] for t in CONFIDENCE_THRESHOLDS}

    for train_start, train_end, test_year in FOLDS:
        train_df = full_df[(full_df["season"] >= train_start) & (full_df["season"] <= train_end)]
        test_df = full_df[full_df["season"] == test_year]

        df_train, X_train, y_train, feature_cols = prepare(train_df, exclude)
        df_test, X_test, y_test, _ = prepare(test_df, exclude)

        if len(df_train) < 100 or len(df_test) < 30:
            continue

        imputer = SimpleImputer(strategy="median")
        X_train_imputed = imputer.fit_transform(X_train)
        X_test_imputed = imputer.transform(X_test)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imputed)
        X_test_scaled = scaler.transform(imputer.transform(X_test))

        model = LogisticRegression(max_iter=2000, C=0.1, random_state=42)
        model.fit(X_train_scaled, y_train)
        probs = model.predict_proba(X_test_scaled)[:, 1]

        for conf in CONFIDENCE_THRESHOLDS:
            confident_home = probs >= conf
            confident_away = probs <= (1 - conf)
            bet_mask = confident_home | confident_away
            if bet_mask.sum() == 0:
                continue

            predicted_home_covers = confident_home[bet_mask]
            actual_home_covers = y_test.values[bet_mask]
            correct = predicted_home_covers == actual_home_covers.astype(bool)
            wins = int(correct.sum())
            total = len(correct)

            pooled_by_threshold[conf][0] += wins
            pooled_by_threshold[conf][1] += total
            year_results_by_threshold[conf].append((test_year, wins / total * 100, total))

    print("=== 'WITHOUT recruiting' across ALL confidence thresholds ===\n")
    for conf in CONFIDENCE_THRESHOLDS:
        results = year_results_by_threshold[conf]
        wins, total = pooled_by_threshold[conf]
        if total == 0:
            continue

        print(f"Confidence >= {conf}:")
        above = 0
        for year, rate, n in results:
            marker = " <-- above breakeven" if rate >= 52.4 else ""
            if rate >= 52.4:
                above += 1
            print(f"    {year}: {rate:.1f}% (n={n}){marker}")

        avg = sum(r for _, r, _ in results) / len(results)
        vs_chance = binomtest(wins, total, p=0.5, alternative="greater")
        vs_breakeven = binomtest(wins, total, p=BREAKEVEN, alternative="greater")
        print(f"    AVG: {avg:.1f}% | {above}/{len(results)} years above breakeven")
        print(f"    POOLED: {wins}/{total} = {wins/total*100:.1f}% | "
              f"vs 50%: p={vs_chance.pvalue:.4f} | vs 52.4%: p={vs_breakeven.pvalue:.4f}")
        print()


if __name__ == "__main__":
    run()