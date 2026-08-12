import os
import time
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Player, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def _upsert_player(db, p, team_id, seen_ids, counters):
    player_id = getattr(p, "id", None)
    if player_id is None:
        return

    first_name = getattr(p, "first_name", None)
    last_name = getattr(p, "last_name", None)
    full_name = f"{first_name or ''} {last_name or ''}".strip() or None

    fields = dict(
        name=full_name,
        first_name=first_name,
        last_name=last_name,
        position=getattr(p, "position", None),
        team_id=team_id,
        class_year=getattr(p, "year", None),
        height=getattr(p, "height", None),
        weight=getattr(p, "weight", None),
        home_city=getattr(p, "home_city", None),
        home_state=getattr(p, "home_state", None),
        home_country=getattr(p, "home_country", None),
        recruit_ids=getattr(p, "recruit_ids", None),
    )

    if player_id in seen_ids:
        # Already processed this run (e.g. mid-year transfer listed on two
        # rosters) - this later listing wins, since it's presumably closer
        # to the player's current/final team for that season.
        existing = db.query(Player).filter(Player.id == player_id).first()
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            counters["updated"] += 1
        return

    seen_ids.add(player_id)
    existing = db.query(Player).filter(Player.id == player_id).first()

    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        counters["updated"] += 1
    else:
        db.add(Player(id=player_id, **fields))
        counters["inserted"] += 1


def sync_roster_for_year(year: int, tracker: ApiUsageTracker):
    """
    Rosters are pulled per-team (no bulk 'all teams' option). Commits after
    EACH team, not once for the whole year - so a failure partway through
    doesn't erase all prior progress, and each team's data is durable
    immediately. seen_ids tracks players already processed this run, to
    correctly handle same-year duplicates (e.g. mid-year transfers CFBD
    lists on two rosters).
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    teams = db.query(Team).filter(Team.is_verified == True).all()
    counters = {"inserted": 0, "updated": 0}
    failed_teams = []
    seen_ids = set()

    with cfbd.ApiClient(configuration) as api_client:
        teams_api = cfbd.TeamsApi(api_client)

        for i, team in enumerate(teams):
            try:
                roster = teams_api.get_roster(team=team.school, year=year)
                tracker.tick()
            except Exception:
                failed_teams.append(team.school)
                continue

            try:
                for p in roster:
                    _upsert_player(db, p, team.id, seen_ids, counters)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"    Failed to save roster for {team.school}: {e}")
                failed_teams.append(team.school)

            time.sleep(0.05)

            if (i + 1) % 50 == 0:
                print(f"    ...{i + 1}/{len(teams)} teams processed "
                      f"(inserted {counters['inserted']}, updated {counters['updated']} so far)")

    db.close()
    print(f"  Year {year}: inserted {counters['inserted']}, updated {counters['updated']} "
          f"(failed teams: {len(failed_teams)})")
    if failed_teams:
        print(f"    Failed: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")


def backfill_rosters(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_rosters")
    print(f"Backfilling rosters from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_roster_for_year(year, tracker)
    tracker.report()


def sync_current_roster(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_roster")
    sync_roster_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_rosters()

def sync_roster_for_year(year: int, tracker: ApiUsageTracker, team_filter: list = None):
    """
    Rosters are pulled per-team (no bulk 'all teams' option). Commits after
    EACH team, not once for the whole year - so a failure partway through
    doesn't erase all prior progress, and each team's data is durable
    immediately. seen_ids tracks players already processed this run, to
    correctly handle same-year duplicates (e.g. mid-year transfers CFBD
    lists on two rosters).

    team_filter: optional list of school names to restrict this run to -
    useful for testing before a full backfill.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    query = db.query(Team).filter(Team.is_verified == True)
    if team_filter:
        query = query.filter(Team.school.in_(team_filter))
    teams = query.all()

    counters = {"inserted": 0, "updated": 0}
    failed_teams = []
    seen_ids = set()

    with cfbd.ApiClient(configuration) as api_client:
        teams_api = cfbd.TeamsApi(api_client)

        for i, team in enumerate(teams):
            try:
                roster = teams_api.get_roster(team=team.school, year=year)
                tracker.tick()
            except Exception:
                failed_teams.append(team.school)
                continue

            try:
                for p in roster:
                    _upsert_player(db, p, team.id, seen_ids, counters)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"    Failed to save roster for {team.school}: {e}")
                failed_teams.append(team.school)

            time.sleep(0.05)

            if (i + 1) % 50 == 0:
                print(f"    ...{i + 1}/{len(teams)} teams processed "
                      f"(inserted {counters['inserted']}, updated {counters['updated']} so far)")

    db.close()
    print(f"  Year {year}: inserted {counters['inserted']}, updated {counters['updated']} "
          f"(failed teams: {len(failed_teams)})")
    if failed_teams:
        print(f"    Failed: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")