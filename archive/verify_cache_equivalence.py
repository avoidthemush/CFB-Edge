"""
Proves the cached feature builder produces IDENTICAL output to the
original per-query version, before trusting it for bulk dataset
generation. Run this after any change to the caching logic.
"""
from app.db import SessionLocal
from app.models import Game
from app.features.build_game_features import build_game_features
from app.features.feature_cache import FeatureCache

db = SessionLocal()

test_games = db.query(Game).filter(
    Game.season == 2025, Game.completed == True
).limit(100).all()

cache = FeatureCache(2025, 2025)

mismatches = 0
for game in test_games:
    uncached = build_game_features(game.id, db=db)
    cached = build_game_features(game.id, db=db, cache=cache)

    for key in uncached:
        u_val = uncached.get(key)
        c_val = cached.get(key)
        if u_val != c_val:
            if isinstance(u_val, float) and isinstance(c_val, float) and abs(u_val - c_val) < 1e-9:
                continue
            print(f"MISMATCH game {game.id}, field '{key}': uncached={u_val} vs cached={c_val}")
            mismatches += 1

db.close()
print(f"\n{'PASS - identical output' if mismatches == 0 else f'FAIL - {mismatches} mismatches found'} (tested {len(test_games)} games)")