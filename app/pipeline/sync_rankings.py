import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import PollRanking, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_rankings_for_year(year: int, tracker: ApiUsageTracker):
    """
    One bulk call per year returns every week's polls (AP, Coaches, CFP
    Committee) in a nested structure: PollWeek -> Poll -> PollRank.
    Flattened into one row per (team, year, week, poll).
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    updated = 0
    skipped = 0
    skipped_names = set()

    try:
        with cfbd.ApiClient(configuration) as api_client:
            rankings_api = cfbd.RankingsApi(api_client)
            poll_weeks = rankings_api.get_rankings(year=year)
            tracker.tick()

            for pw in poll_weeks:
                week = getattr(pw, "week", None)

                for poll in getattr(pw, "polls", []) or []:
                    poll_name = getattr(poll, "poll", None)

                    for rank_entry in getattr(poll, "ranks", []) or []:
                        team_name = getattr(rank_entry, "school", None)
                        team_id = resolve_team_id(team_name, school_to_id)

                        if team_id is None:
                            skipped += 1
                            skipped_names.add(team_name)
                            continue

                        fields = dict(
                            rank=getattr(rank_entry, "rank", None),
                            points=getattr(rank_entry, "points", None),
                        )

                        existing = db.query(PollRanking).filter(
                            PollRanking.team_id == team_id,
                            PollRanking.year == year,
                            PollRanking.week == week,
                            PollRanking.poll == poll_name,
                        ).first()

                        if existing:
                            for key, value in fields.items():
                                setattr(existing, key, value)
                            updated += 1
                        else:
                            db.add(PollRanking(
                                team_id=team_id, year=year, week=week, poll=poll_name, **fields
                            ))
                            inserted += 1

            db.commit()
            print(f"  Year {year}: inserted {inserted}, updated {updated} (skipped {skipped} no team match)")
            if skipped_names:
                print(f"    Skipped: {list(skipped_names)[:10]}")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_rankings(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_rankings")
    print(f"Backfilling poll rankings from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_rankings_for_year(year, tracker)
    tracker.report()


def sync_current_rankings(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_rankings")
    sync_rankings_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_rankings()