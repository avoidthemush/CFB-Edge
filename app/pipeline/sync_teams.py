import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Team
from app.pipeline.api_usage import ApiUsageTracker

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_teams(year: int = 2025):
    """
    Teams are mostly static year-to-year (conference realignment is the main
    thing that changes), but we still pass a year so conference membership
    reflects that season correctly.
    """
    tracker = ApiUsageTracker("sync_teams")
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    inserted = 0
    updated = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            api_instance = cfbd.TeamsApi(api_client)
            teams = api_instance.get_teams(year=year)
            tracker.tick()

            for t in teams:
                location = getattr(t, "location", None)
                latitude = getattr(location, "latitude", None) if location else None
                longitude = getattr(location, "longitude", None) if location else None
                is_dome = getattr(location, "dome", False) if location else False

                existing = db.query(Team).filter(Team.id == t.id).first()

                fields = dict(
                    school=t.school,
                    conference=getattr(t, "conference", None),
                    division=getattr(t, "classification", None),
                    latitude=latitude,
                    longitude=longitude,
                    is_dome=bool(is_dome),
                )

                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(Team(id=t.id, **fields))
                    inserted += 1

            db.commit()
            print(f"Teams sync complete - inserted: {inserted}, updated: {updated}")

    except Exception as e:
        db.rollback()
        print(f"Teams sync FAILED: {e}")
        raise
    finally:
        db.close()
        tracker.report()


if __name__ == "__main__":
    sync_teams(year=2025)