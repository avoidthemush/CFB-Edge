import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Venue
from app.pipeline.api_usage import ApiUsageTracker

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_venues():
    """
    Venues are near-static reference data - re-run occasionally (annual
    maintenance covers this) to catch new/renamed venues.

    Important: CFBD doesn't have lat/long for every venue. Some of ours
    were manually geocoded via OpenWeather as a one-time fix (see
    geocode_missing_venues.py). This sync must never overwrite a real
    coordinate with CFBD's None - it only fills gaps or updates a field
    when CFBD actually provides a non-null value.
    """
    tracker = ApiUsageTracker("sync_venues")
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    inserted = 0
    updated = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            api_instance = cfbd.VenuesApi(api_client)
            venues = api_instance.get_venues()
            tracker.tick()

            for v in venues:
                existing = db.query(Venue).filter(Venue.id == v.id).first()

                cfbd_fields = dict(
                    name=v.name,
                    city=getattr(v, "city", None),
                    state=getattr(v, "state", None),
                    latitude=getattr(v, "latitude", None),
                    longitude=getattr(v, "longitude", None),
                    capacity=getattr(v, "capacity", None),
                    is_dome=bool(getattr(v, "dome", False)),
                    surface=getattr(v, "grass", None),
                    elevation=getattr(v, "elevation", None),
                )

                if existing:
                    for key, value in cfbd_fields.items():
                        # Never let a None from CFBD overwrite existing data
                        # (protects manually-geocoded coordinates, etc.)
                        if value is not None:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(Venue(id=v.id, **cfbd_fields))
                    inserted += 1

            db.commit()
            print(f"Venues sync complete - inserted: {inserted}, updated: {updated}")

    except Exception as e:
        db.rollback()
        print(f"Venues sync FAILED: {e}")
        raise
    finally:
        db.close()
        tracker.report()


if __name__ == "__main__":
    sync_venues()