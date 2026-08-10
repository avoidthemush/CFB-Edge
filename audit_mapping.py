from app.db import SessionLocal
from app.models import Team, Venue, Game

db = SessionLocal()

print("=== TEAMS ===")
total_teams = db.query(Team).count()
verified_teams = db.query(Team).filter(Team.is_verified == True).count()
stub_teams = db.query(Team).filter(Team.is_verified == False).count()
print(f"Total: {total_teams} | Verified (real CFBD): {verified_teams} | Stubs: {stub_teams}")

print("\n=== VENUES ===")
print(f"Total: {db.query(Venue).count()}")

print("\n=== GAMES ===")
print(f"Total: {db.query(Game).count()}")

print("\n=== REFERENTIAL INTEGRITY ===")
games_missing_home = db.query(Game).filter(~Game.home_team_id.in_(db.query(Team.id))).count()
games_missing_away = db.query(Game).filter(~Game.away_team_id.in_(db.query(Team.id))).count()
games_missing_venue = db.query(Game).filter(
    Game.venue_id.isnot(None),
    ~Game.venue_id.in_(db.query(Venue.id))
).count()
print(f"Games with unresolved home_team_id: {games_missing_home}")
print(f"Games with unresolved away_team_id: {games_missing_away}")
print(f"Games with unresolved venue_id: {games_missing_venue}")

print("\n=== STUB TEAMS (need review) ===")
stubs = db.query(Team).filter(Team.is_verified == False).all()
for s in stubs:
    game_count = db.query(Game).filter(
        (Game.home_team_id == s.id) | (Game.away_team_id == s.id)
    ).count()
    print(f"  [{s.id}] {s.school} - appears in {game_count} game(s)")

db.close()