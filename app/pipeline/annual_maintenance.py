"""
Run this once per offseason (ideally after conference realignment news
settles, before the season's first games are backfilled) to bring the
whole database current for the new season.

Before running: update CURRENT_SEASON in app/config.py to the new year.

This script only orchestrates - each step's real logic lives in its own
module (sync_teams.py, sync_venues.py, etc.). Add new steps here as new
data categories get built, rather than writing separate yearly scripts.
"""

from app.pipeline.sync_venues import sync_venues
from app.pipeline.sync_teams import sync_teams
from app.pipeline.sync_games import sync_current_season
from app.pipeline.build_odds_crosswalk import build_crosswalk
from app.db import SessionLocal
from app.models import Team, Venue, Game, TeamSourceAlias
from app.config import CURRENT_SEASON


def run_final_audit():
    print("\n" + "=" * 50)
    print("FINAL AUDIT")
    print("=" * 50)
    db = SessionLocal()

    total_teams = db.query(Team).count()
    verified_teams = db.query(Team).filter(Team.is_verified == True).count()
    stub_teams = db.query(Team).filter(Team.is_verified == False).count()
    print(f"Teams: {total_teams} total ({verified_teams} verified, {stub_teams} stubs)")

    total_venues = db.query(Venue).count()
    missing_coords = db.query(Venue).filter(
        (Venue.latitude.is_(None)) | (Venue.longitude.is_(None))
    ).count()
    print(f"Venues: {total_venues} total ({missing_coords} missing coordinates)")

    current_season_games = db.query(Game).filter(Game.season == CURRENT_SEASON).count()
    print(f"Games ({CURRENT_SEASON} season): {current_season_games}")

    unresolved_aliases = db.query(TeamSourceAlias).filter(
        TeamSourceAlias.source == "odds_api",
        TeamSourceAlias.team_id.is_(None)
    ).count()
    unverified_aliases = db.query(TeamSourceAlias).filter(
        TeamSourceAlias.source == "odds_api",
        TeamSourceAlias.team_id.isnot(None),
        TeamSourceAlias.verified == False
    ).count()
    print(f"Odds API crosswalk: {unresolved_aliases} unresolved, {unverified_aliases} need review")

    if unresolved_aliases > 0 or unverified_aliases > 0:
        print("\n>>> ACTION NEEDED: new/unmatched team names found - review before trusting odds sync <<<")
    else:
        print("\nAll clear.")

    db.close()


def run_annual_maintenance():
    print(f"Running annual maintenance for {CURRENT_SEASON} season\n")

    print("--- Step 1: Venues ---")
    sync_venues()

    print("\n--- Step 2: Teams ---")
    sync_teams(year=CURRENT_SEASON)

    print("\n--- Step 3: Current season games ---")
    sync_current_season(year=CURRENT_SEASON)

    print("\n--- Step 4: Odds API crosswalk (new/renamed teams only) ---")
    build_crosswalk()

    run_final_audit()


if __name__ == "__main__":
    run_annual_maintenance()