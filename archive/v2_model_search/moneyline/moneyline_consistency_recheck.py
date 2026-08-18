"""
Second-split confirmation for the Type C consistency signal, focused on
pct=0.15 (the ROI standout from Phase 1) - checking whether it holds on
an independent internal split before considering a real look at 2025.
"""
import pandas as pd
from app.models_ml.moneyline.margin_to_probability import spread_to_implied_win_probability
from app.models_ml.moneyline.devig import devig_two_way

MIN_ABS_SPREAD = 3
STAKE = 100
PCT = 0.15


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


def evaluate(df, pct):
    low_cutoff = df["consistency_gap"].quantile(pct)
    high_cutoff = df["consistency_gap"].quantile(1 - pct)

    bullish_home = df[df["consistency_gap"] >= high_cutoff].copy()
    bullish_home["won"] = bullish_home["home_won"]
    bullish_home["profit"] = bullish_home.apply(lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1)

    bullish_away = df[df["consistency_gap"] <= low_cutoff].copy()
    bullish_away["won"] = ~bullish_away["home_won"]
    bullish_away["profit"] = bullish_away.apply(lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1)

    all_bets = pd.concat([bullish_home, bullish_away])
    total_bets, total_wins = len(all_bets), int(all_bets["won"].sum())
    total_profit = all_bets["profit"].sum()
    roi = (total_profit / (total_bets * STAKE) * 100) if total_bets > 0 else 0
    win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    return total_wins, total_bets, win_rate, total_profit, roi


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    for label, train_end, val_year in [("train 2021-2023, validate 2024 (original)", 2023, 2024),
                                        ("train 2021-2022, validate 2023 (recheck)", 2022, 2023)]:
        val_df = prepare(full_df[full_df["season"] == val_year])
        wins, total, win_rate, profit, roi = evaluate(val_df, PCT)
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"{label}: {wins}/{total} = {win_rate:.1f}% | ${profit:+.0f} profit | ROI={roi:+.1f}%{marker}")


if __name__ == "__main__":
    run()