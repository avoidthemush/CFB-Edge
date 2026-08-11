from app.db import SessionLocal
from app.models import Venue

db = SessionLocal()

for name in ["Hornet", "Sac State", "Sacramento"]:
    matches = db.query(Venue).filter(Venue.name.ilike(f"%{name}%")).all()
    if matches:
        for v in matches:
            print(f"Match for '{name}': {v.name} ({v.city}, {v.state})")
    else:
        print(f"No match for '{name}'")

db.close()