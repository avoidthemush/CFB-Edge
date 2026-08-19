"""
Breaks down where time is actually going in predict_week.py's runtime -
cache read vs. get_live_book_lines() vs. model inference - to see if
there's a real, fixable bottleneck before treating 35-42s as final.
"""
import time
from app.db import SessionLocal
from app.models import Game, GameFeatureCache
from app.features.get_game_line import get_live_book_lines

db = SessionLocal()

t0 = time.time()
cache_rows = db.query(GameFeatureCache).join(Game).filter(Game.season == 2026).all()
cache_rows = [r for r in cache_rows if r.features.get("week") == 1]
t1 = time.time()
print(f"Cache read: {t1-t0:.2f}s for {len(cache_rows)} games")

t2 = time.time()
for row in cache_rows:
    get_live_book_lines(row.game_id, db)
t3 = time.time()
print(f"get_live_book_lines() for all {len(cache_rows)} games: {t3-t2:.2f}s "
      f"({(t3-t2)/len(cache_rows)*1000:.0f}ms per game)")

db.close()