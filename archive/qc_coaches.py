from app.db import SessionLocal
from app.models import Coach, CoachSeason, Team

db = SessionLocal()

print("=== Orphan check: coach_seasons.coach_id ===")
valid_coach_ids = {c.id for c in db.query(Coach.id).all()}
orphans = db.query(CoachSeason).filter(~CoachSeason.coach_id.in_(valid_coach_ids)).count()
print(f"Orphaned coach_id: {orphans}")

print("\n=== Orphan check: coach_seasons.team_id ===")
valid_team_ids = {t.id for t in db.query(Team.id).all()}
team_orphans = db.query(CoachSeason).filter(
    CoachSeason.team_id.isnot(None),
    ~CoachSeason.team_id.in_(valid_team_ids)
).count()
print(f"Orphaned team_id: {team_orphans}")

print("\n=== Null team_id (unresolved school names) ===")
null_team = db.query(CoachSeason).filter(CoachSeason.team_id.is_(None)).count()
total = db.query(CoachSeason).count()
print(f"Null: {null_team}/{total}")

print("\n=== Field completeness ===")
for field in ["wins", "losses", "win_percentage", "srs", "sp_overall"]:
    col = getattr(CoachSeason, field)
    n = db.query(CoachSeason).filter(col.isnot(None)).count()
    print(f"  {field}: {n}/{total} ({n/total*100:.1f}%)")

print("\n=== Sample: current Alabama coach ===")
alabama = db.query(Team).filter(Team.school == "Alabama").first()
recent = db.query(CoachSeason).filter(
    CoachSeason.team_id == alabama.id, CoachSeason.year == 2025
).first()
if recent:
    coach = db.query(Coach).filter(Coach.id == recent.coach_id).first()
    print(f"  {coach.first_name} {coach.last_name}: {recent.wins}-{recent.losses}, "
          f"SP+ overall: {recent.sp_overall}")

db.close()