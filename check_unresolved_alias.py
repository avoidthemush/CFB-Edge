from app.db import SessionLocal
from app.models import TeamSourceAlias

db = SessionLocal()

total = db.query(TeamSourceAlias).filter(TeamSourceAlias.source == "odds_api").count()
null_team_id = db.query(TeamSourceAlias).filter(
    TeamSourceAlias.source == "odds_api",
    TeamSourceAlias.team_id.is_(None)
).all()

print(f"Total odds_api alias rows: {total}")
print(f"Rows with no team_id (unresolved): {len(null_team_id)}")
for row in null_team_id:
    print(f"  [{row.id}] '{row.source_name}' - confidence: {row.confidence}, verified: {row.verified}")

db.close()