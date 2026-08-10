from app.db import SessionLocal
from app.models import TeamSourceAlias

db = SessionLocal()

updated = db.query(TeamSourceAlias).filter(
    TeamSourceAlias.source == "odds_api",
    TeamSourceAlias.team_id.isnot(None)
).update({TeamSourceAlias.verified: True})

db.commit()
db.close()

print(f"Marked {updated} odds_api aliases as verified")