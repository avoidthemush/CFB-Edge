from app.models_ml.moneyline.margin_to_probability import spread_to_implied_win_probability

test_cases = [0, -2.5, -3.5, -7, -14, -21, -28, 2.5, 7, 14]
print("Home team's spread -> implied win probability")
for spread in test_cases:
    prob = spread_to_implied_win_probability(spread)
    print(f"  spread={spread:+.1f}: win probability={prob*100:.1f}%")