"""
Year-by-year check on the two strongest situational findings: far
travel alone, and the far-travel + big-prior-win combo. Same discipline
as every system tonight - a promising pooled number means nothing
until we confirm it's not concentrated in one or two lucky years.
"""
import pandas as pd

STAKE = 100


def american_odds_profit(odds, won):
    if not won:
        return -STAKE
    if odds > 0:
        return odds
    return STAKE * (100 / -odds)


def run():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    full_df = full_df[
        full_df["market_spread_open"].notna() & full_df["actual_spread"].notna() &
        full_df["market_home_moneyline"].notna() & full_df["market_away_moneyline"].notna()
    ].copy()
    full_df = full_df[full_df["market_spread_open"] != 0]

    full_df["home_is_dog"] = full_df["market_spread_open"] > 0
    full_df["dog_spread_size"] = full_df["market_spread_open"].abs()
    full_df["dog_ml"] = full_df.apply(lambda r: r["market_home_moneyline"] if r["home_is_dog"] else r["market_away_moneyline"], axis=1)
    full_df["dog_won"] = full_df.apply(lambda r: (r["actual_spread"] > 0) if r["home_is_dog"] else (r["actual_spread"] < 0), axis=1)

    home_dogs = full_df[full_df["home_is_dog"] & (full_df["dog_spread_size"] <= 10)].copy()

    scenarios = {
        "Far travel alone (>500mi)": home_dogs["away_travel_distance"] > 500,
        "Combo: far travel + big prior win": (home_dogs["away_travel_distance"] > 500) & (home_dogs["away_last_game_margin"] >= 21),
    }

    for label, mask in scenarios.items():
        print(f"\n=== {label} ===")
        subset = home_dogs[mask].copy()
        pooled_profit, pooled_n, pooled_wins = 0, 0, 0
        for year in sorted(subset["season"].unique()):
            year_df = subset[subset["season"] == year].copy()
            if len(year_df) < 5:
                print(f"  {year}: n={len(year_df)}, too few")
                continue
            year_df["profit"] = year_df.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
            win_rate = year_df["dog_won"].mean() * 100
            profit = year_df["profit"].sum()
            roi = profit / (len(year_df) * STAKE) * 100
            marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
            print(f"  {year}: n={len(year_df)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}")
            pooled_profit += profit
            pooled_n += len(year_df)
            pooled_wins += year_df["dog_won"].sum()
        if pooled_n > 0:
            print(f"  POOLED: n={pooled_n}, win={pooled_wins/pooled_n*100:.1f}%, ROI={pooled_profit/(pooled_n*STAKE)*100:+.1f}%")


if __name__ == "__main__":
    run()