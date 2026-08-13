import os
import time
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import TeamStatWeekly, TeamAdvancedStatWeekly, Team, RatingSnapshot
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

MAX_REGULAR_SEASON_WEEK = 15  # covers regular season; postseason weeks not point-in-time relevant the same way


def _extract_stat_value(raw_value):
    value = getattr(raw_value, "actual_instance", raw_value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sync_weekly_team_stats_for_year(year: int, tracker: ApiUsageTracker):
    """
    One call per week (through_week=1, 2, 3...) rather than one call per
    season - this is the point-in-time version. Delete-and-replace per
    (year, through_week) since there's no stable per-stat ID.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()
    school_to_id = {t.school: t.id for t in db.query(Team).all()}

    total_inserted = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            stats_api = cfbd.StatsApi(api_client)

            for week in range(1, MAX_REGULAR_SEASON_WEEK + 1):
                results = stats_api.get_team_stats(year=year, end_week=week)
                tracker.tick()

                db.query(TeamStatWeekly).filter(
                    TeamStatWeekly.year == year,
                    TeamStatWeekly.through_week == week,
                ).delete()

                if not results:
                    continue

                inserted = 0
                for r in results:
                    team_id = resolve_team_id(getattr(r, "team", None), school_to_id)
                    if team_id is None:
                        continue

                    value = _extract_stat_value(getattr(r, "stat_value", None))
                    if value is None:
                        continue

                    db.add(TeamStatWeekly(
                        team_id=team_id, year=year, through_week=week,
                        category=getattr(r, "stat_name", None), stat_value=value,
                    ))
                    inserted += 1

                db.commit()
                total_inserted += inserted
                time.sleep(0.05)

            print(f"  Year {year}: {total_inserted} total rows across weeks 1-{MAX_REGULAR_SEASON_WEEK}")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def sync_weekly_advanced_stats_for_year(year: int, tracker: ApiUsageTracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()
    school_to_id = {t.school: t.id for t in db.query(Team).all()}

    total_inserted = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            stats_api = cfbd.StatsApi(api_client)

            for week in range(1, MAX_REGULAR_SEASON_WEEK + 1):
                results = stats_api.get_advanced_season_stats(year=year, end_week=week)
                tracker.tick()

                db.query(TeamAdvancedStatWeekly).filter(
                    TeamAdvancedStatWeekly.year == year,
                    TeamAdvancedStatWeekly.through_week == week,
                ).delete()

                if not results:
                    continue

                inserted = 0
                for r in results:
                    team_id = resolve_team_id(getattr(r, "team", None), school_to_id)
                    if team_id is None:
                        continue

                    db.add(TeamAdvancedStatWeekly(
                        team_id=team_id, year=year, through_week=week,
                        raw_json=r.to_dict() if hasattr(r, "to_dict") else None,
                    ))
                    inserted += 1

                db.commit()
                total_inserted += inserted
                time.sleep(0.05)

            print(f"  Year {year}: {total_inserted} total rows across weeks 1-{MAX_REGULAR_SEASON_WEEK}")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def sync_weekly_elo_for_year(year: int, tracker: ApiUsageTracker):
    """Reuses rating_snapshots - just populates the week column, system='elo'."""
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()
    school_to_id = {t.school: t.id for t in db.query(Team).all()}

    total_inserted = 0
    total_updated = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            ratings_api = cfbd.RatingsApi(api_client)

            for week in range(1, MAX_REGULAR_SEASON_WEEK + 1):
                try:
                    results = ratings_api.get_elo(year=year, week=week)
                    tracker.tick()
                except Exception:
                    continue

                for r in results:
                    team_id = resolve_team_id(getattr(r, "team", None), school_to_id)
                    if team_id is None:
                        continue

                    elo_value = getattr(r, "elo", None)

                    existing = db.query(RatingSnapshot).filter(
                        RatingSnapshot.team_id == team_id,
                        RatingSnapshot.year == year,
                        RatingSnapshot.week == week,
                        RatingSnapshot.system == "elo",
                    ).first()

                    if existing:
                        existing.rating = elo_value
                        total_updated += 1
                    else:
                        db.add(RatingSnapshot(
                            team_id=team_id, year=year, week=week, system="elo", rating=elo_value,
                        ))
                        total_inserted += 1

                db.commit()
                time.sleep(0.05)

            print(f"  Year {year}: inserted {total_inserted}, updated {total_updated}")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_weekly_stats(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_weekly_stats")
    for year in range(start_year, end_year + 1):
        print(f"\n--- {year} team stats (weekly) ---")
        sync_weekly_team_stats_for_year(year, tracker)
        print(f"--- {year} advanced stats (weekly) ---")
        sync_weekly_advanced_stats_for_year(year, tracker)
        print(f"--- {year} Elo (weekly) ---")
        sync_weekly_elo_for_year(year, tracker)
    tracker.report()


def sync_current_weekly_stats(year: int = CURRENT_SEASON):
    """
    Annual-maintenance-friendly version - syncs weekly point-in-time
    data for just the current season, not the full historical range.
    """
    tracker = ApiUsageTracker("sync_current_weekly_stats")
    print(f"  Team stats (weekly, {year})...")
    sync_weekly_team_stats_for_year(year, tracker)
    print(f"  Advanced stats (weekly, {year})...")
    sync_weekly_advanced_stats_for_year(year, tracker)
    print(f"  Elo (weekly, {year})...")
    sync_weekly_elo_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_weekly_stats()