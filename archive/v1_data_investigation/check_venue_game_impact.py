from app.db import SessionLocal
from app.models import Venue, Game

db = SessionLocal()

missing_venues = db.query(Venue).filter(
    (Venue.latitude.is_(None)) | (Venue.longitude.is_(None))
).all()

results = []
for v in missing_venues:
    game_count = db.query(Game).filter(Game.venue_id == v.id).count()
    if game_count > 0:
        results.append((game_count, v.name, v.city, v.state))

results.sort(reverse=True)

print(f"{len(results)} of the 38 missing-coordinate venues are actually used in games:\n")
for count, name, city, state in results:
    print(f"  {count} game(s) - {name} ({city}, {state})")

db.close()