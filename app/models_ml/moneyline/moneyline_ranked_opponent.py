"""
New angle, untested tonight: does facing a RANKED favorite change the
value of betting the underdog, within the FLB sweet spot (slight dogs,
spread<=10)? Real hypothesis: public perception/name-brand bias toward
ranked teams could make underdogs-vs-ranked-teams worse value (public
money floods the ranked favorite, pushing the line further from fair),
while underdogs-vs-unranked-but-favored teams face less of that bias.
"""
import pandas as pd

STAKE = 100
MAX_DOG_SPREAD = 10


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
    full_df["favorite_is_ranked"] = full_df.apply(
        lambda r: r["away_is_ranked"] if r["home_is_dog"] else r["home_is_ranked"], axis=1
    )

    dog_pool = full_df[full_df["dog_spread_size"] <= MAX_DOG_SPREAD].copy()

    for ranked_status, label in [(1, "Favorite IS ranked"), (0, "Favorite NOT ranked")]:
        subset = dog_pool[dog_pool["favorite_is_ranked"] == ranked_status].copy()
        if len(subset) < 20:
            print(f"{label}: only {len(subset)}, too few")
            continue
        subset["profit"] = subset.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
        win_rate = subset["dog_won"].mean() * 100
        profit = subset["profit"].sum()
        roi = profit / (len(subset) * STAKE) * 100
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"{label}: n={len(subset)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}")

        print("  By year:")
        for year in sorted(subset["season"].unique()):
            year_df = subset[subset["season"] == year].copy()
            if len(year_df) < 5:
                continue
            year_df["profit"] = year_df.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
            yroi = year_df["profit"].sum() / (len(year_df) * STAKE) * 100
            ymarker = "PROFITABLE" if yroi > 0 else "LOSING"
            print(f"    {year}: n={len(year_df)}, ROI={yroi:+.1f}% ({ymarker})")
        print()


if __name__ == "__main__":
    run()