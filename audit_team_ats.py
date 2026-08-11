from app.db import SessionLocal
from app.models import TeamATS, Team
from sqlalchemy import func

db = SessionLocal()

total = db.query(TeamATS).filter(TeamATS.year == 2025).count()
distinct_teams = db.query(func.count(func.distinct(TeamATS.team_id))).filter(TeamATS.year == 2025).scalar()
print(f"2025: {total} rows, {distinct_teams} distinct teams")

print("\nField completeness (2025):")
for name, col in [("ats_wins", TeamATS.ats_wins), ("ats_losses", TeamATS.ats_losses), ("ats_pushes", TeamATS.ats_pushes)]:
    n = db.query(TeamATS).filter(TeamATS.year == 2025, col.isnot(None)).count()
    print(f"  {name}: {n}/{total}")

print("\nSample row (Alabama, 2025):")
alabama = db.query(Team).filter(Team.school == "Alabama").first()
sample = db.query(TeamATS).filter(TeamATS.team_id == alabama.id, TeamATS.year == 2025).first()
if sample:
    print(f"  wins={sample.ats_wins}, losses={sample.ats_losses}, pushes={sample.ats_pushes}")
    print(f"  raw_json: {sample.raw_json}")
else:
    print("  No row found for Alabama 2025")

db.close()