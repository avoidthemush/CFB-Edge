from app.db import SessionLocal
from app.models import Venue

db = SessionLocal()

total = db.query(Venue).count()
missing_coords = db.query(Venue).filter(
    (Venue.latitude.is_(None)) | (Venue.longitude.is_(None))
).count()
missing_dome_flag = db.query(Venue).filter(Venue.is_dome.is_(None)).count()

print(f"Total venues: {total}")
print(f"Missing lat/long: {missing_coords}")
print(f"Missing is_dome flag: {missing_dome_flag}")

if missing_coords > 0:
    print("\nVenues missing coordinates:")
    for v in db.query(Venue).filter(
        (Venue.latitude.is_(None)) | (Venue.longitude.is_(None))
    ).limit(20).all():
        print(f"  [{v.id}] {v.name} ({v.city}, {v.state})")

db.close()