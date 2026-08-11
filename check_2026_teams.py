from app.db import SessionLocal
from app.models import Team

db = SessionLocal()

total = db.query(Team).count()
print(f"Total teams in database: {total}")

fbs_count = db.query(Team).filter(Team.division == "fbs").count()
print(f"FBS teams: {fbs_count}")

db.close()