from app.db import SessionLocal
from app.models import TeamSourceAlias

db = SessionLocal()
deleted = db.query(TeamSourceAlias).filter(TeamSourceAlias.source == "odds_api").delete()
db.commit()
db.close()

print(f"Deleted {deleted} existing odds_api alias rows")