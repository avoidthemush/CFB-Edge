import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import TeamAdvancedStat, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_advanced_stats_for_year(year: int, tracker: ApiUsageTracker):
    """
    Opponent-adjusted efficiency stats. Stored as raw JSONB since the
    nested shape (offense/defense splits, situational breakdowns) is
    complex and best flattened into model features later rather than
    hand-modeled into relational columns now.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    updated = 0
    skipped = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            stats_api = cfbd.StatsApi(api_client)
            results = stats_api.get_advanced_season_stats(year=year)
            tracker.tick()

            for r in results:
                team_name = getattr(r, "team", None)
                team_id = school_to_id.get(team_name)

                if team_id is None:
                    skipped += 1
                    continue

                raw = r.to_dict() if hasattr(r, "to_dict") else None

                existing = db.query(TeamAdvancedStat).filter(
                    TeamAdvancedStat.team_id == team_id,
                    TeamAdvancedStat.year == year,
                ).first()

                if existing:
                    existing.raw_json = raw
                    updated += 1
                else:
                    db.add(TeamAdvancedStat(team_id=team_id, year=year, raw_json=raw))
                    inserted += 1

            db.commit()
            print(f"  Year {year}: inserted {inserted}, updated {updated} (skipped {skipped} no team match)")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_advanced_stats(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_advanced_stats")
    print(f"Backfilling advanced stats from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_advanced_stats_for_year(year, tracker)
    tracker.report()


def sync_current_advanced_stats(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_advanced_stats")
    sync_advanced_stats_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_advanced_stats()