from app.db import SessionLocal
from app.models import WeatherSnapshot, Game, Venue, Team

db = SessionLocal()

total = db.query(WeatherSnapshot).count()
print(f"Total weather_snapshots rows: {total}")

print("\n=== Field completeness ===")
for field in ["temp_f", "wind_mph", "precip_prob", "condition"]:
    col = getattr(WeatherSnapshot, field)
    n = db.query(WeatherSnapshot).filter(col.isnot(None)).count()
    print(f"  {field}: {n}/{total}")

print("\n=== Sample: Alabama home game, 2025 (outdoor) ===")
alabama = db.query(Team).filter(Team.school == "Alabama").first()
game = db.query(Game).filter(Game.home_team_id == alabama.id, Game.season == 2025).first()
if game:
    snap = db.query(WeatherSnapshot).filter(WeatherSnapshot.game_id == game.id).first()
    if snap:
        print(f"  {game.away_team_name} @ {game.home_team_name}")
        print(f"  Temp: {snap.temp_f}, Wind: {snap.wind_mph}, Precip: {snap.precip_prob}, Condition: {snap.condition}")
    else:
        print("  No weather row found")

print("\n=== Sample: a dome game, 2025 (should be thin/empty) ===")
dome_venue = db.query(Venue).filter(Venue.is_dome == True).first()
dome_game = db.query(Game).filter(Game.venue_id == dome_venue.id, Game.season == 2025).first()
if dome_game:
    snap = db.query(WeatherSnapshot).filter(WeatherSnapshot.game_id == dome_game.id).first()
    print(f"  Venue: {dome_venue.name}")
    if snap:
        print(f"  Temp: {snap.temp_f}, Wind: {snap.wind_mph}, Precip: {snap.precip_prob}, Condition: {snap.condition}")
    else:
        print("  No weather row found (expected for dome)")

db.close()