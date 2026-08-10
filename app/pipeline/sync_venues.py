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
    Venues are near-static reference data (stadiums don't move or get built
    often) - so there's no year parameter here. Run this once, and re-run
    occasionally (e.g., once a year) to catch new/renamed venues.
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

                fields = dict(
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
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(Venue(id=v.id, **fields))
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
