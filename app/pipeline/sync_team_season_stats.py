import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import TeamSeasonStat, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def _extract_stat_value(raw_value):
    value = getattr(raw_value, "actual_instance", raw_value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sync_team_season_stats_for_year(year, tracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    skipped = 0
    skipped_names = set()
    non_numeric = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            stats_api = cfbd.StatsApi(api_client)
            results = stats_api.get_team_stats(year=year)
            tracker.tick()

            db.query(TeamSeasonStat).filter(TeamSeasonStat.year == year).delete()

            for r in results:
                team_name = getattr(r, "team", None)
                team_id = resolve_team_id(team_name, school_to_id)

                if team_id is None:
                    skipped += 1
                    skipped_names.add(team_name)
                    continue

                value = _extract_stat_value(getattr(r, "stat_value", None))
                if value is None:
                    non_numeric += 1
                    continue

                db.add(TeamSeasonStat(
                    team_id=team_id,
                    year=year,
                    category=getattr(r, "stat_name", None),
                    stat_value=value,
                ))
                inserted += 1

            db.commit()
            print("  Year " + str(year) + ": inserted " + str(inserted) +
                  " (skipped " + str(skipped) + " no team match, " +
                  str(non_numeric) + " non-numeric values)")
            if skipped_names:
                print("    Skipped teams: " + str(list(skipped_names)[:10]))

    except Exception as e:
        db.rollback()
        print("  Year " + str(year) + " FAILED: " + str(e))
        raise
    finally:
        db.close()


def backfill_team_season_stats(start_year=HISTORICAL_START_YEAR, end_year=CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_team_season_stats")
    print("Backfilling team season stats from " + str(start_year) + " to " + str(end_year) + "...")
    for year in range(start_year, end_year + 1):
        sync_team_season_stats_for_year(year, tracker)
    tracker.report()


def sync_current_team_season_stats(year=CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_team_season_stats")
    sync_team_season_stats_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_team_season_stats()