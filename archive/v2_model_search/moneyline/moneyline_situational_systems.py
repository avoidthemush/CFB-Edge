"""
User's suggestion: situational systems for dogs, combining slight-dog
status with a REASON the market might be mispricing them - not just an
arbitrary filter. Two concrete, real-world hypotheses tested:
1. Home dog vs an opponent traveling far (tired/disrupted road team)
2. Home dog vs an opponent coming off a big win (letdown spot) or big
   loss (opponent still reeling)

Scoped per user's instruction: dogs only, primary focus. Uses spread
size <= 10 (widened slightly from the 0-3 pure FLB zone to give
situational systems enough sample to test meaningfully) as the
candidate pool, then layers each situational filter on top.
"""
import pandas as pd

STAKE = 100
MAX_DOG_SPREAD = 10  # widened pool - situational filters will narrow it further


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

    dog_pool = full_df[full_df["dog_spread_size"] <= MAX_DOG_SPREAD].copy()

    # Only home dogs make sense for "opponent traveling far" / "opponent's letdown/motivation" -
    # these hypotheses are specifically about the AWAY favorite's situation
    home_dogs = dog_pool[dog_pool["home_is_dog"]].copy()

    print(f"Base pool (home dogs, spread<=10): n={len(home_dogs)}\n")

    scenarios = {
        "Away favorite traveled far (>500mi)": home_dogs["away_travel_distance"] > 500,
        "Away favorite traveled far (>800mi)": home_dogs["away_travel_distance"] > 800,
        "Away favorite off a big win (last margin >=21)": home_dogs["away_last_game_margin"] >= 21,
        "Away favorite off a big loss (last margin <=-14)": home_dogs["away_last_game_margin"] <= -14,
        "Away favorite short rest (<7 days)": home_dogs["away_days_since_last_game"] < 7,
        "Combo: far travel + big prior win (letdown+fatigue)": (home_dogs["away_travel_distance"] > 500) & (home_dogs["away_last_game_margin"] >= 21),
    }

    for label, mask in scenarios.items():
        subset = home_dogs[mask].copy()
        if len(subset) < 20:
            print(f"{label}: only {len(subset)} bets, too few\n")
            continue
        subset["profit"] = subset.apply(lambda r: american_odds_profit(r["dog_ml"], r["dog_won"]), axis=1)
        win_rate = subset["dog_won"].mean() * 100
        profit = subset["profit"].sum()
        roi = profit / (len(subset) * STAKE) * 100
        marker = " <-- PROFITABLE" if roi > 0 else " <-- LOSING"
        print(f"{label}: n={len(subset)}, win={win_rate:.1f}%, ${profit:+.0f}, ROI={roi:+.1f}%{marker}\n")


if __name__ == "__main__":
    run()