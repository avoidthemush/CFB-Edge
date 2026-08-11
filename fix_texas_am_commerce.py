from app.db import SessionLocal
from app.models import TeamSourceAlias

db = SessionLocal()

deleted = db.query(TeamSourceAlias).filter(
    TeamSourceAlias.source == "odds_api",
    TeamSourceAlias.source_name == "Texas A&M-Commerce Lions"
).delete()

db.commit()
db.close()
print(f"Deleted {deleted} row(s) for re-processing")