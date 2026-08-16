from app.db import SessionLocal
from app.models import Team, TeamAdvancedStat, PollRanking
import inspect

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
sample = db.query(TeamAdvancedStat).filter(
    TeamAdvancedStat.team_id == alabama.id, TeamAdvancedStat.year == 2023
).first()

print("=== fieldPosition structure ===")
print("Offense:", sample.raw_json.get("offense", {}).get("fieldPosition"))
print("Defense:", sample.raw_json.get("defense", {}).get("fieldPosition"))

print("\n=== PollRanking columns ===")
for col in PollRanking.__table__.columns:
    print(f"  {col.name}: {col.type}")

print("\n=== PollRanking sample row ===")
sample_rank = db.query(PollRanking).filter(PollRanking.year == 2023).first()
if sample_rank:
    for col in PollRanking.__table__.columns:
        print(f"  {col.name}: {getattr(sample_rank, col.name)}")

db.close()