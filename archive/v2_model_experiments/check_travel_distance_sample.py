from app.db import SessionLocal
from app.models import Team, Venue
from app.features.travel_distance import get_travel_distance_for_game, get_team_home_venue_coords

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
home_lat, home_lon = get_team_home_venue_coords(alabama.id, db=db)
print(f"Alabama home venue coords: {home_lat}, {home_lon}")

# Distance if Alabama played at, say, a West Coast venue
usc = db.query(Team).filter(Team.school == "USC").first()
usc_venue_lat, usc_venue_lon = get_team_home_venue_coords(usc.id, db=db)
print(f"USC home venue coords: {usc_venue_lat}, {usc_venue_lon}")

distance = get_travel_distance_for_game(alabama.id, usc_venue_lat, usc_venue_lon, db=db)
print(f"\nAlabama's travel distance to play at USC: {distance:.0f} miles" if distance else "None")

db.close()