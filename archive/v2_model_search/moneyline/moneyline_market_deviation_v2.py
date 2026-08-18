"""
Second Type B attempt for Moneyline - combined team quality bucketing
(sum of both teams' SP+ rating, not the gap between them) - a genuinely
different question than the discarded rating-gap version: "how good are
both teams overall" rather than "how lopsided is this specific matchup."
"""
import pandas as pd
from app.models_ml.moneyline.devig import devig_two_way

STAKE = 100
PERCENTILE_THRESHOLDS = [0.10, 0.15, 0.20, 0.25]
SAFE_TEST_YEARS = [2022, 2023, 2024]


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


def prepare(df):
    df = df[
        df["market_home_moneyline"].notna() & df["market_away_moneyline"].notna() &
        df["home_sp+_rating"].notna() & df["away_sp+_rating"].notna() & df["actual_spread"].notna()
    ].copy()
    df["combined_sp_rating"] = df["home_sp+_rating"] + df["away_sp+_rating"]
    devig_results = df.apply(
        lambda row: devig_two_way(row["market_home_moneyline"], row["market_away_moneyline"]), axis=1
    )
    df["fair_home_prob"] = devig_results.apply(lambda x: x[0])
    df["home_won"] = df["actual_spread"] > 0
    return df.dropna(subset=["fair_home_prob"])


def build_baseline(train_df):
    train_df = train_df.copy()
    train_df["quality_bucket"] = pd.qcut(train_df["combined_sp_rating"], 10, labels=False, duplicates="drop")
    bins = pd.qcut(train_df["combined_sp_rating"], 10, retbins=True, duplicates="drop")[1]
    bucket_avg_prob = train_df.groupby("quality_bucket")["fair_home_prob"].mean()
    return bins, bucket_avg_prob


def evaluate(test_df, bins, bucket_avg_prob, pct):
    test_df = test_df.copy()
    test_df["quality_bucket"] = pd.cut(test_df["combined_sp_rating"], bins=bins, labels=False, include_lowest=True)
    test_df["expected_home_prob"] = test_df["quality_bucket"].map(bucket_avg_prob)
    test_df["deviation"] = test_df["fair_home_prob"] - test_df["expected_home_prob"]
    test_df = test_df.dropna(subset=["deviation"])

    low_cutoff = test_df["deviation"].quantile(pct)
    high_cutoff = test_df["deviation"].quantile(1 - pct)

    undervalued_home = test_df[test_df["deviation"] <= low_cutoff].copy()
    undervalued_home["won"] = undervalued_home["home_won"]
    undervalued_home["profit"] = undervalued_home.apply(lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1)

    undervalued_away = test_df[test_df["deviation"] >= high_cutoff].copy()
    undervalued_away["won"] = ~undervalued_away["home_won"]
    undervalued_away["profit"] = undervalued_away.apply(lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1)

    all_bets = pd.concat([undervalued_home, undervalued_away])
    if len(all_bets) < 20:
        return None
    roi = all_bets["profit"].sum() / (len(all_bets) * STAKE) * 100
    win_rate = all_bets["won"].mean() * 100
    return roi, len(all_bets), win_rate, all_bets["profit"].sum()


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    for pct in PERCENTILE_THRESHOLDS:
        print(f"\n=== pct={pct} ===")
        for test_year in SAFE_TEST_YEARS:
            train_df = prepare(full_df[full_df["season"] == test_year - 1])
            test_df = prepare(full_df[full_df["season"] == test_year])

            bins, bucket_avg_prob = build_baseline(train_df)
            result = evaluate(test_df, bins, bucket_avg_prob, pct)
            if result is None:
                print(f"  {test_year}: insufficient bets")
                continue
            roi, n, win_rate, profit = result
            marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
            print(f"  {test_year}: {n} bets, {win_rate:.1f}% win, ${profit:+.0f} profit, ROI={roi:+.1f}%{marker}")


if __name__ == "__main__":
    run()