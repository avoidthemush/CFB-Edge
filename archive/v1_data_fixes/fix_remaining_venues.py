from app.db import SessionLocal
from app.models import Venue

# Manually researched - these 3 don't fit the US-only geocoding script
# (2 international venues, 1 CFBD city-name typo "Aracata" instead of "Arcata")
FIXES = {
    11797: (-22.9698, -43.2377),  # Nilton Santos Stadium, Rio de Janeiro, Brazil
    4737: (53.3607, -6.2512),     # Croke Park, Dublin, Ireland
    5118: (40.8665, -124.0828),   # Redwood Bowl, Arcata, CA
}

db = SessionLocal()

for venue_id, (lat, lon) in FIXES.items():
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if venue:
        venue.latitude = lat
        venue.longitude = lon
        print(f"Fixed [{venue_id}] {venue.name} -> ({lat}, {lon})")
    else:
        print(f"[{venue_id}] not found in database")

db.commit()
db.close()