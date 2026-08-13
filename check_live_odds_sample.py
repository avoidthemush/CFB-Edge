from app.db import SessionLocal
from app.models import OddsSnapshot, Game

db = SessionLocal()

total = db.query(OddsSnapshot).count()
print(f"Total odds_snapshots rows: {total}")

books = db.query(OddsSnapshot.sportsbook).distinct().all()
print(f"Sportsbooks: {[b[0] for b in books]}")

sample = db.query(OddsSnapshot).first()
if sample:
    game = db.query(Game).filter(Game.id == sample.game_id).first()
    print(f"\nSample: {game.away_team_name} @ {game.home_team_name}")
    print(f"  Book: {sample.sportsbook}")
    print(f"  Spread: {sample.spread_home} (home price {sample.spread_home_price}, away price {sample.spread_away_price})")
    print(f"  Total: {sample.total} (over {sample.over_price}, under {sample.under_price})")
    print(f"  Moneyline: home {sample.moneyline_home}, away {sample.moneyline_away}")
    print(f"  Pulled at: {sample.pulled_at}")

db.close()