import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import PlayerSeasonStat, Player, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

# Maps (category, statType) from CFBD's tidy format to our column names.
# Confirmed via check_stat_categories.py against a real 2025 pull.
STAT_FIELD_MAP = {
    ("defensive", "TOT"): "tackles_total",
    ("defensive", "SOLO"): "tackles_solo",
    ("defensive", "TFL"): "tackles_for_loss",
    ("defensive", "SACKS"): "sacks",
    ("defensive", "PD"): "passes_defended",
    ("defensive", "QB HUR"): "qb_hurries",
    ("defensive", "TD"): "defensive_tds",
    ("interceptions", "INT"): "interceptions",
    ("interceptions", "YDS"): "interception_yards",
    ("interceptions", "TD"): "interception_tds",
    ("fumbles", "REC"): "fumbles_recovered",
    ("passing", "COMPLETIONS"): "passing_completions",
    ("passing", "ATT"): "passing_attempts",
    ("passing", "YDS"): "passing_yards",
    ("passing", "TD"): "passing_tds",
    ("passing", "INT"): "passing_ints",
    ("rushing", "CAR"): "rushing_carries",
    ("rushing", "YDS"): "rushing_yards",
    ("rushing", "TD"): "rushing_tds",
    ("receiving", "REC"): "receiving_receptions",
    ("receiving", "YDS"): "receiving_yards",
    ("receiving", "TD"): "receiving_tds",
}


def sync_player_stats_for_year(year: int, tracker: ApiUsageTracker):
    """
    One bulk call per year (confirmed via test_stats_bulk_pull.py - no
    need to loop per team). CFBD returns tidy/long format: one row per
    (player, category, statType). We pivot this into one wide row per
    player via player_rows, then write to the database.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    known_player_ids = {p.id for p in db.query(Player.id).all()}

    player_rows = {}  # player_id -> dict of accumulated fields
    skipped_no_team = set()
    skipped_no_player = set()

    try:
        with cfbd.ApiClient(configuration) as api_client:
            stats_api = cfbd.StatsApi(api_client)
            results = stats_api.get_player_season_stats(year=year)
            tracker.tick()

            for r in results:
                player_id = getattr(r, "player_id", None)
                team_name = getattr(r, "team", None)
                category = getattr(r, "category", None)
                stat_type = getattr(r, "stat_type", None)
                stat_value = getattr(r, "stat", None)

                if player_id is None:
                    continue

                # player_id from this endpoint is a string; players.id is int
                try:
                    player_id = int(player_id)
                except (TypeError, ValueError):
                    continue

                if player_id not in known_player_ids:
                    skipped_no_player.add(player_id)
                    continue

                team_id = resolve_team_id(team_name, school_to_id)
                if team_id is None:
                    skipped_no_team.add(team_name)

                if player_id not in player_rows:
                    player_rows[player_id] = {
                        "player_id": player_id,
                        "team_id": team_id,
                        "year": year,
                        "position": getattr(r, "position", None),
                        "raw_json": [],
                    }

                player_rows[player_id]["raw_json"].append(r.to_dict() if hasattr(r, "to_dict") else None)

                field_name = STAT_FIELD_MAP.get((category, stat_type))
                if field_name:
                    try:
                        player_rows[player_id][field_name] = float(stat_value)
                    except (TypeError, ValueError):
                        pass

            inserted = 0
            updated = 0

            for player_id, fields in player_rows.items():
                raw_json = fields.pop("raw_json")

                existing = db.query(PlayerSeasonStat).filter(
                    PlayerSeasonStat.player_id == player_id,
                    PlayerSeasonStat.year == year,
                ).first()

                if existing:
                    for key, value in fields.items():
                        if key not in ("player_id", "year"):
                            setattr(existing, key, value)
                    existing.raw_json = raw_json
                    updated += 1
                else:
                    db.add(PlayerSeasonStat(raw_json=raw_json, **fields))
                    inserted += 1

            db.commit()
            print(
                f"  Year {year}: inserted {inserted}, updated {updated} "
                f"(unknown players: {len(skipped_no_player)}, unresolved teams: {len(skipped_no_team)})"
            )
            if skipped_no_team:
                print(f"    Unresolved team names: {list(skipped_no_team)[:10]}")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_player_stats(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_player_stats")
    print(f"Backfilling player season stats from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_player_stats_for_year(year, tracker)
    tracker.report()


def sync_current_player_stats(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_player_stats")
    sync_player_stats_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_player_stats()