import os
import time
import httpx
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Venue

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def geocode_city_state(city: str, state: str):
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": f"{city},{state},US", "limit": 1, "appid": OPENWEATHER_API_KEY}
    resp = httpx.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data:
        return data[0]["lat"], data[0]["lon"]
    return None, None


def geocode_missing_venues():
    db = SessionLocal()

    missing = db.query(Venue).filter(
        (Venue.latitude.is_(None)) | (Venue.longitude.is_(None))
    ).all()

    fixed = 0
    still_missing = 0

    for v in missing:
        if not v.city or not v.state:
            print(f"  Skipping [{v.id}] {v.name} - no city/state on record")
            still_missing += 1
            continue

        try:
            lat, lon = geocode_city_state(v.city, v.state)
            if lat is not None:
                v.latitude = lat
                v.longitude = lon
                fixed += 1
                print(f"  Fixed [{v.id}] {v.name} -> ({lat}, {lon})")
            else:
                still_missing += 1
                print(f"  No geocode result for [{v.id}] {v.name} ({v.city}, {v.state})")
            time.sleep(0.2)  # be polite to the free-tier rate limit
        except Exception as e:
            still_missing += 1
            print(f"  FAILED [{v.id}] {v.name}: {e}")

    db.commit()
    db.close()
    print(f"\nDone. Fixed: {fixed}, still missing: {still_missing}")


if __name__ == "__main__":
    geocode_missing_venues()