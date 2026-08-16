from app.db import SessionLocal
from app.models import Team, TeamAdvancedStat

db = SessionLocal()
alabama = db.query(Team).filter(Team.school == "Alabama").first()
sample = db.query(TeamAdvancedStat).filter(
    TeamAdvancedStat.team_id == alabama.id, TeamAdvancedStat.year == 2023
).first()

if sample and sample.raw_json:
    print("Offense plays/drives:", sample.raw_json.get("offense", {}).get("plays"),
          sample.raw_json.get("offense", {}).get("drives"))
    print("Defense plays/drives:", sample.raw_json.get("defense", {}).get("plays"),
          sample.raw_json.get("defense", {}).get("drives"))
else:
    print("No sample found")

db.close()