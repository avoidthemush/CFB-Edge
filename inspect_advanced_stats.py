import json
from app.db import SessionLocal
from app.models import TeamAdvancedStat, Team

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
sample = db.query(TeamAdvancedStat).filter(
    TeamAdvancedStat.team_id == alabama.id,
    TeamAdvancedStat.year == 2025,
).first()

if sample:
    print(json.dumps(sample.raw_json, indent=2)[:3000])
else:
    print("No sample found")

db.close()