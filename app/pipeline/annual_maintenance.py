"""
Run this once per offseason (ideally after conference realignment news
settles, before the season's first games are backfilled) to bring the
whole database current for the new season.

Before running: update CURRENT_SEASON in app/config.py to the new year.

This script only orchestrates - each step's real logic lives in its own
module. Add new steps here as new data categories get built, rather than
writing separate yearly scripts.
"""

from app.pipeline.sync_venues import sync_venues
from app.pipeline.sync_teams import sync_teams
from app.pipeline.sync_games import sync_current_season
from app.pipeline.build_odds_crosswalk import build_crosswalk
from app.pipeline.sync_ratings import sync_current_ratings
from app.pipeline.sync_advanced_stats import sync_current_advanced_stats
from app.pipeline.sync_team_ats import sync_current_team_ats
from app.pipeline.sync_team_talent import sync_current_team_talent
from app.pipeline.sync_recruiting import sync_current_recruiting
from app.pipeline.sync_offensive_returning_production import sync_current_returning_production
from app.pipeline.sync_players import sync_current_roster
from app.pipeline.sync_player_stats import sync_current_player_stats
from app.pipeline.sync_player_usage import sync_current_player_usage
from app.pipeline.calc_defensive_returning_production import calc_defensive_returning_production
from app.pipeline.sync_rankings import sync_current_rankings
from app.pipeline.sync_transfer_portal import sync_current_transfer_portal
from app.pipeline.sync_coaches import sync_coaches

from app.db import SessionLocal
from app.models import (
    Team, Venue, Game, TeamSourceAlias, RatingSnapshot, TeamAdvancedStat,
    TeamATS, TeamTalent, RecruitingClass, OffensiveReturningProduction,
    DefensiveReturningProduction, Player, PlayerSeasonStat, PollRanking,
    TransferPortalEntry, Coach, CoachSeason,
)
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

    current_ratings = db.query(RatingSnapshot).filter(RatingSnapshot.year == CURRENT_SEASON).count()
    print(f"Ratings ({CURRENT_SEASON}): {current_ratings} rows")

    current_adv_stats = db.query(TeamAdvancedStat).filter(TeamAdvancedStat.year == CURRENT_SEASON).count()
    print(f"Advanced stats ({CURRENT_SEASON}): {current_adv_stats} rows")

    current_ats = db.query(TeamATS).filter(TeamATS.year == CURRENT_SEASON).count()
    print(f"Team ATS ({CURRENT_SEASON}): {current_ats} rows")

    current_talent = db.query(TeamTalent).filter(TeamTalent.year == CURRENT_SEASON).count()
    print(f"Team talent ({CURRENT_SEASON}): {current_talent} rows")

    current_recruiting = db.query(RecruitingClass).filter(RecruitingClass.year == CURRENT_SEASON).count()
    print(f"Recruiting ({CURRENT_SEASON}): {current_recruiting} rows")

    current_off_rp = db.query(OffensiveReturningProduction).filter(
        OffensiveReturningProduction.year == CURRENT_SEASON
    ).count()
    print(f"Offensive returning production ({CURRENT_SEASON}): {current_off_rp} rows")

    current_def_rp = db.query(DefensiveReturningProduction).filter(
        DefensiveReturningProduction.year == CURRENT_SEASON
    ).count()
    print(f"Defensive returning production ({CURRENT_SEASON}): {current_def_rp} rows")

    current_players = db.query(Player).filter(Player.team_id.isnot(None)).count()
    print(f"Players (current roster snapshot): {current_players} rows")

    current_player_stats = db.query(PlayerSeasonStat).filter(PlayerSeasonStat.year == CURRENT_SEASON).count()
    print(f"Player season stats ({CURRENT_SEASON}): {current_player_stats} rows")

    current_usage = db.query(PlayerSeasonStat).filter(
        PlayerSeasonStat.year == CURRENT_SEASON,
        PlayerSeasonStat.usage_overall.isnot(None)
    ).count()
    print(f"Player usage populated ({CURRENT_SEASON}): {current_usage} rows")

    current_rankings = db.query(PollRanking).filter(PollRanking.year == CURRENT_SEASON).count()
    print(f"Poll rankings ({CURRENT_SEASON}): {current_rankings} rows")

    current_portal = db.query(TransferPortalEntry).filter(TransferPortalEntry.year == CURRENT_SEASON).count()
    print(f"Transfer portal ({CURRENT_SEASON}): {current_portal} rows")

    total_coaches = db.query(Coach).count()
    current_coach_seasons = db.query(CoachSeason).filter(CoachSeason.year == CURRENT_SEASON).count()
    print(f"Coaches: {total_coaches} total, {current_coach_seasons} coach-seasons for {CURRENT_SEASON}")

    if unresolved_aliases > 0 or unverified_aliases > 0:
        print("\n>>> ACTION NEEDED: new/unmatched Odds API team names found - review before trusting odds sync <<<")
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

    print("\n--- Step 5: Ratings (SP+/SRS/Elo/FPI) ---")
    sync_current_ratings(year=CURRENT_SEASON)

    print("\n--- Step 6: Advanced/adjusted stats ---")
    sync_current_advanced_stats(year=CURRENT_SEASON)

    print("\n--- Step 7: Team ATS ---")
    sync_current_team_ats(year=CURRENT_SEASON)

    print("\n--- Step 8: Team talent ---")