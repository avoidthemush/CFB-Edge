from app.db import SessionLocal
from app.models import Team

db = SessionLocal()

for term in ["Houston", "Pine Bluff", "Arkansas"]:
    matches = db.query(Team).filter(Team.school.ilike(f"%{term}%")).all()
    print(f"\nSearch: '{term}'")
    for t in matches:
        print(f"  [{t.id}] '{t.school}' - conference: {t.conference}")

db.close()