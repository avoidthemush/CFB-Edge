from app.db import SessionLocal
from app.models import TeamATS

db = SessionLocal()

rows = db.query(TeamATS).all()
fixed = 0

for row in rows:
    if row.raw_json:
        row.ats_wins = row.raw_json.get("atsWins")
        row.ats_losses = row.raw_json.get("atsLosses")
        row.ats_pushes = row.raw_json.get("atsPushes")
        fixed += 1

db.commit()
db.close()
print(f"Fixed {fixed} rows from existing raw_json - no API calls needed")