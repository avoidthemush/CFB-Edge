from app.db import SessionLocal
from app.models import CFBDBettingLine

PROVIDER_ALIASES = {
    "Draft Kings": "DraftKings",
}

db = SessionLocal()

for bad_name, good_name in PROVIDER_ALIASES.items():
    rows = db.query(CFBDBettingLine).filter(CFBDBettingLine.provider == bad_name).all()
    for row in rows:
        row.provider = good_name
    print(f"Renamed {len(rows)} rows: '{bad_name}' -> '{good_name}'")

db.commit()
db.close()