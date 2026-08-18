"""
Systematic search across percentile thresholds AND situational filters
for the Type C consistency signal - mirrors Total's massive search
approach. ROI (not win rate) computed from the start this time, per the
lesson from the pct=0.15 failure (nearly identical win rates produced
opposite-sign ROI).

Requires a candidate to be ROI-POSITIVE on BOTH 2023 and 2024
independently before flagging it as promising - avoids repeating the
mistake of trusting a single year's result. 2025 held back entirely.
"""
import pandas as pd
from app.models_ml.moneyline.margin_to_probability import spread_to_implied_win_probability
from app.models_ml.moneyline.devig import devig_two_way

MIN_ABS_SPREAD = 3
STAKE = 100
PERCENTILES = [0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25]
TEST_YEARS = [2023, 2024]

FILTERS = {
    "all_games": lambda df: pd.Series(True, index=df.index),
    "home_favorite": lambda df: df["market_spread_open"] < 0,
    "away_favorite": lambda df: df["market_spread_open"] > 0,
    "small_spread": lambda df: df["market_spread_open"].abs() < 7,
    "medium_spread": lambda df: (df["market_spread_open"].abs() >= 7) & (df["market_spread_open"].abs() < 17),
    "large_spread": lambda df: df["market_spread_open"].abs() >= 17,
    "weeks_1_4": lambda df: df["week"] <= 4,
    "weeks_5_plus": lambda df: df["week"] >= 5,
    "conference_games": lambda df: df["is_conference_game"] == 1,
    "non_conference_games": lambda df: df["is_conference_game"] == 0,
}


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


def prepare(df):
    df = df[
        df["market_spread_open"].notna() & df["actual_spread"].notna() &
        df["market_home_moneyline"].notna() & df["market_away_moneyline"].notna()
    ].copy()
    df = df[df["market_spread_open"].abs() >= MIN_ABS_SPREAD]

    df["spread_implied_home_prob"] = df["market_spread_open"].apply(spread_to_implied_win_probability)
    devig_results = df.apply(
        lambda row: devig_two_way(row["market_home_moneyline"], row["market_away_moneyline"]), axis=1
    )
    df["ml_fair_home_prob"] = devig_results.apply(lambda x: x[0])
    df["consistency_gap"] = df["ml_fair_home_prob"] - df["spread_implied_home_prob"]
    df["home_won"] = df["actual_spread"] > 0
    return df.dropna(subset=["consistency_gap"])


def evaluate(df, pct, filter_fn):
    filtered = df[filter_fn(df)]
    if len(filtered) < 30:
        return None

    low_cutoff = filtered["consistency_gap"].quantile(pct)
    high_cutoff = filtered["consistency_gap"].quantile(1 - pct)

    bullish_home = filtered[filtered["consistency_gap"] >= high_cutoff].copy()
    bullish_home["won"] = bullish_home["home_won"]
    bullish_home["profit"] = bullish_home.apply(lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1)

    bullish_away = filtered[filtered["consistency_gap"] <= low_cutoff].copy()
    bullish_away["won"] = ~bullish_away["home_won"]
    bullish_away["profit"] = bullish_away.apply(lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1)

    all_bets = pd.concat([bullish_home, bullish_away])
    total_bets = len(all_bets)
    if total_bets < 20:
        return None

    total_profit = all_bets["profit"].sum()
    roi = total_profit / (total_bets * STAKE) * 100
    win_rate = all_bets["won"].mean() * 100
    return roi, total_bets, win_rate, total_profit


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    prepared_by_year = {year: prepare(full_df[full_df["season"] == year]) for year in TEST_YEARS}

    results = []
    for pct in PERCENTILES:
        for filter_name, filter_fn in FILTERS.items():
            year_results = {}
            for year in TEST_YEARS:
                r = evaluate(prepared_by_year[year], pct, filter_fn)
                if r is not None:
                    year_results[year] = r

            if len(year_results) < len(TEST_YEARS):
                continue

            both_positive = all(year_results[y][0] > 0 for y in TEST_YEARS)
            if not both_positive:
                continue

            avg_roi = sum(year_results[y][0] for y in TEST_YEARS) / len(TEST_YEARS)
            total_bets = sum(year_results[y][1] for y in TEST_YEARS)
            results.append((pct, filter_name, avg_roi, total_bets, year_results))

    results.sort(key=lambda x: -x[2])

    print(f"Tested {len(PERCENTILES) * len(FILTERS)} combinations across {TEST_YEARS}")
    print(f"Candidates with POSITIVE ROI on BOTH years: {len(results)}\n")

    print("=== ALL qualifying candidates (both years ROI-positive), sorted by avg ROI ===")
    for pct, filter_name, avg_roi, total_bets, year_results in results:
        detail = ", ".join(f"{y}: ROI={year_results[y][0]:+.1f}% ({year_results[y][1]} bets, "
                            f"{year_results[y][2]:.1f}% win)" for y in TEST_YEARS)
        print(f"  pct={pct}, filter={filter_name}: avg ROI={avg_roi:+.1f}%, total {total_bets} bets")
        print(f"    {detail}")


if __name__ == "__main__":
    run()