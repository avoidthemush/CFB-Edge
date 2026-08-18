"""
Type C test: does a mismatch between the book's OWN spread-implied win
probability and its OWN devigged moneyline probability predict anything
real? Uses REAL ROI based on actual American odds per bet, NOT a flat
52.4% breakeven (that threshold only applies to standard -110 spread/
total bets - moneyline odds vary bet-to-bet, so win rate alone can't
tell us if this is actually profitable).

Excludes |spread| < 3 games (near pick'em, confirmed real market
ambiguity earlier tonight). Phase 1: train/calibrate 2021-2023,
validate 2024. 2025 held back.
"""
import pandas as pd
from app.models_ml.moneyline.margin_to_probability import spread_to_implied_win_probability
from app.models_ml.moneyline.devig import devig_two_way

MIN_ABS_SPREAD = 3
PERCENTILE_THRESHOLDS = [0.10, 0.15, 0.20, 0.25]
STAKE = 100


def american_odds_profit(odds, won):
    """Profit/loss on a $100 stake if this bet won or lost."""
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    else:
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
    df = df.dropna(subset=["consistency_gap"])
    return df


def evaluate(df, percentile):
    low_cutoff = df["consistency_gap"].quantile(percentile)
    high_cutoff = df["consistency_gap"].quantile(1 - percentile)

    bullish_home = df[df["consistency_gap"] >= high_cutoff].copy()
    bullish_home["won"] = bullish_home["home_won"]
    bullish_home["profit"] = bullish_home.apply(
        lambda r: american_odds_profit(r["market_home_moneyline"], r["won"]), axis=1
    )

    bullish_away = df[df["consistency_gap"] <= low_cutoff].copy()
    bullish_away["won"] = ~bullish_away["home_won"]
    bullish_away["profit"] = bullish_away.apply(
        lambda r: american_odds_profit(r["market_away_moneyline"], r["won"]), axis=1
    )

    all_bets = pd.concat([bullish_home, bullish_away])
    total_bets = len(all_bets)
    total_wins = int(all_bets["won"].sum())
    total_profit = all_bets["profit"].sum()
    total_staked = total_bets * STAKE
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0
    win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0

    return total_wins, total_bets, win_rate, total_profit, roi


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df = full_df[full_df["season"] <= 2024]

    train_df = prepare(full_df[full_df["season"] <= 2023])
    val_df = prepare(full_df[full_df["season"] == 2024])

    print(f"Train (calibration reference, 2021-2023): {len(train_df)} games")
    print(f"Validate (2024): {len(val_df)} games\n")

    print("=== Validation results by percentile threshold - REAL ROI, not win rate vs flat breakeven ===")
    for pct in PERCENTILE_THRESHOLDS:
        wins, total, win_rate, profit, roi = evaluate(val_df, pct)
        if total == 0:
            print(f"  pct={pct}: no bets")
            continue
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"  pct={pct}: {wins}/{total} = {win_rate:.1f}% win rate | "
              f"${profit:+.0f} profit on ${total*STAKE} staked | ROI={roi:+.1f}%{marker}")


if __name__ == "__main__":
    run()