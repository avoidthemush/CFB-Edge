import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import RecruitingClass, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_recruiting_for_year(year: int, tracker: ApiUsageTracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    updated = 0
    skipped = 0
    skipped_names = []

    try:
        with cfbd.ApiClient(configuration) as api_client:
            recruiting_api = cfbd.RecruitingApi(api_client)
            results = recruiting_api.get_team_recruiting_rankings(year=year)
            tracker.tick()

            for r in results:
                team_name = getattr(r, "team", None)
                team_id = resolve_team_id(team_name, school_to_id)

                if team_id is None:
                    skipped += 1
                    skipped_names.append(team_name)
                    continue

                fields = dict(
                    rank=getattr(r, "rank", None),
                    points=getattr(r, "points", None),
                    raw_json=r.to_dict() if hasattr(r, "to_dict") else None,
                )

                existing = db.query(RecruitingClass).filter(
                    RecruitingClass.team_id == team_id,
                    RecruitingClass.year == year,
                ).first()

                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(RecruitingClass(team_id=team_id, year=year, **fields))
                    inserted += 1

            db.commit()
            print(f"  Year {year}: inserted {inserted}, updated {updated} (skipped {skipped} no team match)")
            if skipped_names:
                print(f"    Skipped: {skipped_names}")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_recruiting(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_recruiting")
    print(f"Backfilling recruiting classes from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_recruiting_for_year(year, tracker)
    tracker.report()


def sync_current_recruiting(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_recruiting")
    sync_recruiting_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_recruiting()