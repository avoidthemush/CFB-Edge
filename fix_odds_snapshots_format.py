from app.db import SessionLocal
from app.models import OddsSnapshot

db = SessionLocal()
deleted = db.query(OddsSnapshot).delete()
db.commit()
db.close()

print(f"Deleted {deleted} corrupted odds_snapshots rows (wrong odds format)")