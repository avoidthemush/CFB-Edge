import os
import cfbd
from dotenv import load_dotenv
from datetime import datetime

from app.db import SessionLocal
from app.models import Game, Team
from app.pipeline.api_usage import ApiUsageTracker

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

HISTORICAL_START_YEAR = 2021
CURRENT_YEAR = 2026


def _parse_start_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _ensure_team_exists(db, team_id, team_name, known_ids: set):
    """
    Games occasionally reference small-school opponents (Division II, etc.)
    that never appear in CFBD's main teams endpoint in any year. Rather than
    let that break the whole games sync, create a minimal placeholder record
    so the foreign key is satisfied. If a real sync_teams pull ever does
    pick this team up, it'll get filled in properly at that point.
    """
    if team_id is None or team_id in known_ids:
        return

    existing = db.query(Team).filter(Team.id == team_id).first()
    if existing:
        known_ids.add(team_id)
        return

    db.add(Team(
        id=team_id,
        school=team_name or f"Unknown team {team_id}",
        conference=None,
        division=None,
        latitude=None,
        longitude=None,
        is_dome=False,
        is_verified=False,
    ))
    known_ids.add(team_id)


def sync_games_for_year(year: int, tracker: ApiUsageTracker):
    """
    Pulls every game (regular + postseason) for a single season in one API
    call, then upserts each into the games table. This same function backs
    both the historical backfill (looped across years) and the ongoing
    dynamic sync (called with just the current year on a schedule).
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    inserted = 0
    updated = 0
    stub_teams_created = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            api_instance = cfbd.GamesApi(api_client)
            games = api_instance.get_games(year=year, season_type="both")
            tracker.tick()

            known_ids = {row.id for row in db.query(Team.id).all()}
            starting_known_count = len(known_ids)

            for g in games:
                home_id = getattr(g, "home_id", None)
                away_id = getattr(g, "away_id", None)

                _ensure_team_exists(db, home_id, getattr(g, "home_team", None), known_ids)
                _ensure_team_exists(db, away_id, getattr(g, "away_team", None), known_ids)

                existing = db.query(Game).filter(Game.id == g.id).first()

                fields = dict(
                    season=g.season,
                    week=g.week,
                    season_type=getattr(g, "season_type", "regular"),
                    start_date=_parse_start_date(getattr(g, "start_date", None)),
                    home_team_id=home_id,
                    away_team_id=away_id,
                    home_team_name=getattr(g, "home_team", None),
                    away_team_name=getattr(g, "away_team", None),
                    home_points=getattr(g, "home_points", None),
                    away_points=getattr(g, "away_points", None),
                    venue_id=getattr(g, "venue_id", None),
                    venue=getattr(g, "venue", None),
                    neutral_site=bool(getattr(g, "neutral_site", False)),
                    attendance=getattr(g, "attendance", None),
                    completed=bool(getattr(g, "completed", False)),
                )

                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(Game(id=g.id, **fields))
                    inserted += 1

            db.commit()
            stub_teams_created = len(known_ids) - starting_known_count
            print(
                f"  Year {year}: inserted {inserted}, updated {updated} "
                f"(total {len(games)}), stub teams created: {stub_teams_created}"
            )

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_games(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_YEAR):
    """
    One-time (or rarely re-run) historical backfill across every season
    from start_year to end_year.
    """
    tracker = ApiUsageTracker("backfill_games")
    print(f"Backfilling games from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_games_for_year(year, tracker)
    tracker.report()


def sync_current_season(year: int = CURRENT_YEAR):
    """
    Ongoing dynamic sync - call this on a schedule (weekly, or daily during
    the season) to pick up newly scheduled games and new results.
    """
    tracker = ApiUsageTracker("sync_current_season")
    sync_games_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_games()