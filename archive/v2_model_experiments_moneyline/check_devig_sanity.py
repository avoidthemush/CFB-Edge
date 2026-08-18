from app.models_ml.moneyline.devig import american_odds_to_implied_prob, devig_two_way

# A real row from our own data: spread_open=-6.0, home_ml=-250, away_ml=+210
print("Raw implied probabilities:")
print(f"  home_ml=-250: {american_odds_to_implied_prob(-250)*100:.1f}%")
print(f"  away_ml=+210: {american_odds_to_implied_prob(210)*100:.1f}%")
print(f"  Sum (should be > 100% due to vig): "
      f"{(american_odds_to_implied_prob(-250) + american_odds_to_implied_prob(210))*100:.1f}%")

fair_home, fair_away = devig_two_way(-250, 210)
print(f"\nDevigged (fair) probabilities:")
print(f"  home: {fair_home*100:.1f}%")
print(f"  away: {fair_away*100:.1f}%")
print(f"  Sum (should be exactly 100%): {(fair_home + fair_away)*100:.1f}%")