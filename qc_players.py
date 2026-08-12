from app.db import SessionLocal
from app.models import Player, Team
from sqlalchemy import func

db = SessionLocal()

print("=== 1. Total players ===")
total = db.query(Player).count()
print(f"Total: {total}")

print("\n=== 2. Orphaned team references (player.team_id not in teams) ===")
valid_team_ids = {t.id for t in db.query(Team.id).all()}
orphans = db.query(Player).filter(~Player.team_id.in_(valid_team_ids)).all()
print(f"Orphaned: {len(orphans)}")
for o in orphans[:10]:
    print(f"  [{o.id}] {o.name} -> team_id {o.team_id}")

print("\n=== 3. Null team_id ===")
null_team = db.query(Player).filter(Player.team_id.is_(None)).count()
print(f"Players with no team: {null_team}")

print("\n=== 4. Roster size per team (current snapshot) - flagging outliers ===")
counts = (
    db.query(Team.school, func.count(Player.id))
    .join(Player, Player.team_id == Team.id)
    .group_by(Team.school)
    .all()
)
low = [(s, c) for s, c in counts if c < 20]
high = [(s, c) for s, c in counts if c > 150]
print(f"Teams with < 20 players: {len(low)}")
for s, c in sorted(low, key=lambda x: x[1])[:15]:
    print(f"  {s}: {c}")
print(f"\nTeams with > 150 players: {len(high)}")
for s, c in sorted(high, key=lambda x: -x[1])[:15]:
    print(f"  {s}: {c}")

print("\n=== 5. Field completeness ===")
for field in ["position", "class_year", "height", "weight", "home_city", "home_state"]:
    col = getattr(Player, field)
    n = db.query(Player).filter(col.isnot(None)).count()
    print(f"  {field}: {n}/{total} ({n/total*100:.1f}%)")

print("\n=== 6. Distinct position values (checking for consistency/junk values) ===")
positions = db.query(Player.position, func.count(Player.id)).group_by(Player.position).order_by(func.count(Player.id).desc()).all()
for pos, count in positions:
    print(f"  {pos}: {count}")

print("\n=== 7. Possible duplicate people (same name, same team) ===")
dupes = (
    db.query(Player.name, Player.team_id, func.count(Player.id))
    .filter(Player.name.isnot(None))
    .group_by(Player.name, Player.team_id)
    .having(func.count(Player.id) > 1)
    .all()
)
print(f"Same name + same team, different IDs: {len(dupes)}")
for name, team_id, count in dupes[:15]:
    print(f"  '{name}' (team_id {team_id}): {count} different player IDs")

db.close()