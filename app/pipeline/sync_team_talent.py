import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import TeamTalent, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_team_talent_for_year(year: int, tracker: ApiUsageTracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    updated = 0
    skipped = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            teams_api = cfbd.TeamsApi(api_client)
            results = teams_api.get_talent(year=year)
            tracker.tick()

            for r in results:
                team_name = getattr(r, "team", None)
                team_id = school_to_id.get(team_name)

                if team_id is None:
                    skipped += 1
                    continue

                talent_score = getattr(r, "talent", None)

                existing = db.query(TeamTalent).filter(
                    TeamTalent.team_id == team_id,
                    TeamTalent.year == year,
                ).first()

                if existing:
                    existing.talent_score = talent_score
                    updated += 1
                else:
                    db.add(TeamTalent(team_id=team_id, year=year, talent_score=talent_score))
                    inserted += 1

            db.commit()
            print(f"  Year {year}: inserted {inserted}, updated {updated} (skipped {skipped} no team match)")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_team_talent(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_team_talent")
    print(f"Backfilling team talent from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_team_talent_for_year(year, tracker)
    tracker.report()


def sync_current_team_talent(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_team_talent")
    sync_team_talent_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_team_talent()