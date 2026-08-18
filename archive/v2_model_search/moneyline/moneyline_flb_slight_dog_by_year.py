"""
Year-by-year breakdown of the one profitable FLB bucket (slight dogs,
spread 0-3) - confirming the pooled +1.5% ROI isn't hiding one great
year propping up four bad ones, same discipline as every system tonight.
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

    full_df["home_is_dog"] = full_df["market_spread_open"] > 0
    full_df["dog_spread_size"] = full_df["market_spread_open"].abs()
    full_df["dog_ml"] = full_df.apply(lambda r: r["market_home_moneyline"] if r["home_is_dog"] else r["market_away_moneyline"], axis=1)
    full_df["dog_won"] = full_df.apply(lambda r: (r["actual_spread"] > 0) if r["home_is_dog"] else (r["actual_spread"] < 0), axis=1)
    full_df = full_df[full_df["market_spread_open"] != 0]

    bucket = full_df[(full_df["dog_spread_size"] >= 0) & (full_df["dog_spread_size"] < 3)].copy()

    print("=== Slight dog (spread 0-3), BY YEAR ===\n")
    pooled_profit, pooled_n, pooled_wins = 0, 0, 0
    for year in sorted(bucket["season"].unique()):
        year_df = bucket[bucket["season"] == year].copy()
        year_df["profit"] = year_df.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
        win_rate = year_df["dog_won"].mean() * 100
        profit = year_df["profit"].sum()
        roi = profit / (len(year_df) * STAKE) * 100
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"  {year}: n={len(year_df)}, win={win_rate:.1f}%, ${profit:+.0f} profit, ROI={roi:+.1f}%{marker}")
        pooled_profit += profit
        pooled_n += len(year_df)
        pooled_wins += year_df["dog_won"].sum()

    print(f"\nPOOLED: n={pooled_n}, win={pooled_wins/pooled_n*100:.1f}%, "
          f"${pooled_profit:+.0f} profit, ROI={pooled_profit/(pooled_n*STAKE)*100:+.1f}%")


if __name__ == "__main__":
    run()