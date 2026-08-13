import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import PlayerSeasonStat, Player
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def sync_player_usage_for_year(year: int, tracker: ApiUsageTracker):
    """
    Confirmed via test_usage_bulk_pull.py and check_usage_by_position.py:
    this endpoint only covers offensive skill positions (QB/RB/WR/TE/FB) -
    not defensive positions. That's expected, not a bug - the defensive
    metric intentionally uses havoc counts instead (see
    calc_defensive_returning_production.py). This just fills in
    usage_overall on player_season_stats for the offensive players it
    does cover, enabling player-level (not just team-level) usage
    concentration analysis later.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    known_player_ids = {p.id for p in db.query(Player.id).all()}
    updated = 0
    skipped_no_stat_row = 0
    skipped_no_player = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            players_api = cfbd.PlayersApi(api_client)
            results = players_api.get_player_usage(year=year)
            tracker.tick()

            for r in results:
                player_id = getattr(r, "id", None)
                if player_id is None:
                    continue

                try:
                    player_id = int(player_id)
                except (TypeError, ValueError):
                    continue

                if player_id not in known_player_ids:
                    skipped_no_player += 1
                    continue

                overall_usage = r.usage.overall if getattr(r, "usage", None) else None

                stat_row = db.query(PlayerSeasonStat).filter(
                    PlayerSeasonStat.player_id == player_id,
                    PlayerSeasonStat.year == year,
                ).first()

                if stat_row:
                    stat_row.usage_overall = overall_usage
                    updated += 1
                else:
                    skipped_no_stat_row += 1

            db.commit()
            print(f"  Year {year}: updated {updated} "
                  f"(no matching stat row: {skipped_no_stat_row}, unknown player: {skipped_no_player})")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_player_usage(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_player_usage")
    print(f"Backfilling player usage from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_player_usage_for_year(year, tracker)
    tracker.report()


def sync_current_player_usage(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_player_usage")
    sync_player_usage_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_player_usage()