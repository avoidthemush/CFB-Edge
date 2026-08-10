from app.db import SessionLocal
from app.models import Team

db = SessionLocal()

matches = db.query(Team).filter(Team.school.ilike("%app%")).all()
print("Teams with 'app' in the name:")
for t in matches:
    print(f"  [{t.id}] '{t.school}' - conference: {t.conference}, verified: {t.is_verified}")

db.close()