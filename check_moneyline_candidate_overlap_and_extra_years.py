"""
Two checks before trusting any of these candidates: (1) do weeks_1_4
and conference_games overlap heavily, or are they independent slices,
and (2) do the two strongest candidates hold up on 2021/2022 too - real
extra confirmation given the small samples and suspiciously high win
rates already seen (reminiscent of the earlier Spread stepwise-search
overfitting trap).
"""
import pandas as pd
from app.models_ml.moneyline.margin_to_probability import spread_to_implied_win_probability
from app.models_ml.moneyline.devig import devig_two_way

MIN_ABS_SPREAD = 3
STAKE = 100


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
    devig_results = df.apply(lambda row: devig_two_way(row["market_home_moneyline"], row["market_away_moneyline"]), axis=1)
    df["ml_fair_home_prob"] = devig_results.apply(lambda x: x[0])
    df["consistency_gap"] = df["ml_fair_home_prob"] - df["spread_implied_home_prob"]
    df["home_won"] = df["actual_spread"] > 0
    return df.dropna(subset=["consistency_gap"])


def evaluate(df, pct, filter_fn):
    filtered = df[filter_fn(df)]
    if len(filtered) < 15:
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
    if len(all_bets) == 0:
        return None
    roi = all_bets["profit"].sum() / (len(all_bets) * STAKE) * 100
    return roi, len(all_bets), all_bets["won"].mean() * 100


full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
full_df = full_df[full_df["season"] <= 2024]

print("=== Overlap check: weeks 1-4 vs conference games (all years) ===")
check_df = full_df[full_df["market_spread_open"].notna()]
weeks_1_4 = check_df["week"] <= 4
conf_games = check_df["is_conference_game"] == 1
print(f"Weeks 1-4 games: {weeks_1_4.sum()}")
print(f"Conference games: {conf_games.sum()}")
print(f"Overlap (both weeks 1-4 AND conference): {(weeks_1_4 & conf_games).sum()}")
print(f"Weeks 1-4 that are ALSO conference games: {(weeks_1_4 & conf_games).sum() / weeks_1_4.sum() * 100:.1f}%")

print("\n=== Extra-year confirmation: weeks_1_4 candidates on 2021 and 2022 ===")
for pct in [0.05, 0.15]:
    print(f"\npct={pct}, filter=weeks_1_4:")
    for year in [2021, 2022]:
        year_df = prepare(full_df[full_df["season"] == year])
        result = evaluate(year_df, pct, lambda df: df["week"] <= 4)
        if result is None:
            print(f"  {year}: insufficient data")
            continue
        roi, n, win_rate = result
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"  {year}: {n} bets, {win_rate:.1f}% win, ROI={roi:+.1f}%{marker}")