"""
Faster version using FeatureCache - avoids rebuilding expensive lookups
(coach H2H index, etc.) from scratch on every single game, which is
what made the uncached version slow across 211 games.
"""
from app.db import SessionLocal
from app.models import Game
from app.features.feature_cache import FeatureCache
from app.features.build_game_features import build_game_features
from app.models_ml.total.predict_week import load_artifacts, evaluate_system

db = SessionLocal()
print("Building cache for 2026 (this is a one-time cost, not per-game)...")
cache = FeatureCache(start_year=2026, end_year=2026)

artifacts = load_artifacts()

games = db.query(Game).filter(Game.season == 2026, Game.week == 1, Game.completed == False).all()
print(f"\nChecking {len(games)} games...")

checked = 0
for game in games:
    features = build_game_features(game.id, db=db, cache=cache, game=game)
    if features is None or features.get("market_total_open") is None:
        continue
    result = evaluate_system("wind_deviation", artifacts["wind_deviation"], features)
    checked += 1
    if result is not None:
        print(f"{game.away_team_name} @ {game.home_team_name}: wind={features.get('wind_mph')}, "
              f"spread_open={features.get('market_spread_open')}, fires={result.get('fires')}, "
              f"deviation={result.get('deviation')}")

print(f"\nChecked {checked} games with valid market lines")
db.close()