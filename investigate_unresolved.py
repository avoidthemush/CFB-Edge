from app.db import SessionLocal
from app.models import Team

db = SessionLocal()

search_terms = ["Southern", "Albany", "Appalachian", "LIU", "Long Island", "Southeastern Louisiana", "SE Louisiana"]

for term in search_terms:
    matches = db.query(Team).filter(Team.school.ilike(f"%{term}%")).all()
    print(f"\nSearch: '{term}'")
    for t in matches:
        print(f"  [{t.id}] '{t.school}' - conference: {t.conference}, verified: {t.is_verified}")

db.close()