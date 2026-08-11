import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import ReturningProduction, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_returning_production_for_year(year: int, tracker: ApiUsageTracker):
    """
    CFBD's returning production is offense-only. Captures every field the
    endpoint provides (not just a simplified overall/offense split), since
    we don't yet know which specific fields will end up mattering as model
    features - better to have them queryable now than rediscover the need
    later. Defense side has no CFBD equivalent - handled separately.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    updated = 0
    skipped = 0
    skipped_names = []

    try:
        with cfbd.ApiClient(configuration) as api_client:
            players_api = cfbd.PlayersApi(api_client)
            results = players_api.get_returning_production(year=year)
            tracker.tick()

            for r in results:
                team_name = getattr(r, "team", None)
                team_id = resolve_team_id(team_name, school_to_id)

                if team_id is None:
                    skipped += 1
                    skipped_names.append(team_name)
                    continue

                fields = dict(
                    total_ppa=getattr(r, "total_ppa", None),
                    total_passing_ppa=getattr(r, "total_passing_ppa", None),
                    total_receiving_ppa=getattr(r, "total_receiving_ppa", None),
                    total_rushing_ppa=getattr(r, "total_rushing_ppa", None),
                    percent_ppa=getattr(r, "percent_ppa", None),
                    percent_passing_ppa=getattr(r, "percent_passing_ppa", None),
                    percent_receiving_ppa=getattr(r, "percent_receiving_ppa", None),
                    percent_rushing_ppa=getattr(r, "percent_rushing_ppa", None),
                    usage=getattr(r, "usage", None),
                    passing_usage=getattr(r, "passing_usage", None),
                    receiving_usage=getattr(r, "receiving_usage", None),
                    rushing_usage=getattr(r, "rushing_usage", None),
                    raw_json=r.to_dict() if hasattr(r, "to_dict") else None,
                )

                existing = db.query(ReturningProduction).filter(
                    ReturningProduction.team_id == team_id,
                    ReturningProduction.year == year,
                ).first()

                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(ReturningProduction(team_id=team_id, year=year, **fields))
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


def backfill_returning_production(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_returning_production")
    print(f"Backfilling returning production from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_returning_production_for_year(year, tracker)
    tracker.report()


def sync_current_returning_production(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_returning_production")
    sync_returning_production_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_returning_production()