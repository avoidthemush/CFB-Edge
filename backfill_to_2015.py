"""
One-time historical extension: 2021 -> 2015 for everything that
supports it, with ATS starting 2019 and transfer portal staying 2021
(real CFBD limitations, not choices). Calls existing, already-tested
backfill_*() functions with explicit start_year overrides - no changes
to the underlying sync logic itself.

Run in stages, not all at once - the roster and weekly-stats backfills
are expensive (time, not API cost) and worth checking in on separately.
"""
from app.pipeline.sync_teams import sync_teams
from app.pipeline.sync_games import backfill_games
from app.pipeline.sync_betting_lines import backfill_cfbd_lines
from app.pipeline.sync_ratings import backfill_ratings
from app.pipeline.sync_advanced_stats import backfill_advanced_stats
from app.pipeline.sync_team_season_stats import backfill_team_season_stats
from app.pipeline.sync_recruiting import backfill_recruiting
from app.pipeline.sync_rankings import backfill_rankings
from app.pipeline.sync_team_talent import backfill_team_talent
from app.pipeline.sync_team_ats import backfill_team_ats
from app.pipeline.sync_weather import backfill_historical_weather
from app.pipeline.sync_players import backfill_rosters
from app.pipeline.sync_player_stats import backfill_player_stats
from app.pipeline.sync_player_usage import backfill_player_usage
from app.pipeline.sync_offensive_returning_production import backfill_returning_production
from app.pipeline.sync_weekly_stats import backfill_weekly_stats
from app.pipeline.calc_defensive_returning_production import calc_defensive_returning_production
from app.pipeline.calc_coach_tendencies import calc_coach_tendencies


def stage_1_teams_and_games():
    """
    Cheap, fast - foundation everything else depends on.

    IMPORTANT: teams.division/conference are NOT year-scoped columns -
    they just hold whatever the most recent sync_teams() call set them
    to. Looping years in ascending order here previously left the table
    reflecting 2020's classification, silently misclassifying every
    team that transitioned into FBS since (caught via a suspicious
    FBS-filter row-count drop, fixed Aug 2026 - see DESIGN_DECISIONS.md).
    Historical years are synced first, then CURRENT_SEASON is synced
    LAST, so the table always ends up reflecting today's real
    classification, not a leftover historical year.
    """
    from app.config import CURRENT_SEASON

    print("=== Stage 1: Teams (2015-2020, historical) ===")
    for year in range(2015, 2021):
        sync_teams(year=year)

    print(f"\n=== Stage 1: Teams (restoring current {CURRENT_SEASON} classification) ===")
    sync_teams(year=CURRENT_SEASON)

    print("\n=== Stage 1: Games (2015-2020) ===")
    backfill_games(start_year=2015, end_year=2020)


def stage_2_lines_ratings_stats():
    """Cheap - a handful of calls per source."""
    print("=== Stage 2: Betting lines ===")
    backfill_cfbd_lines(start_year=2015, end_year=2020)

    print("\n=== Stage 2: Ratings ===")
    backfill_ratings(start_year=2015, end_year=2020)

    print("\n=== Stage 2: Advanced stats ===")
    backfill_advanced_stats(start_year=2015, end_year=2020)

    print("\n=== Stage 2: Team season stats (raw box score) ===")
    backfill_team_season_stats(start_year=2015, end_year=2020)


def stage_3_context_data():
    """Cheap - recruiting, rankings, talent, ATS, weather."""
    print("=== Stage 3: Recruiting ===")
    backfill_recruiting(start_year=2015, end_year=2020)

    print("\n=== Stage 3: Rankings ===")
    backfill_rankings(start_year=2015, end_year=2020)

    print("\n=== Stage 3: Team talent ===")
    backfill_team_talent(start_year=2015, end_year=2020)

    print("\n=== Stage 3: Team ATS (2019-2020 only - genuinely unavailable before) ===")
    backfill_team_ats(start_year=2019, end_year=2020)

    print("\n=== Stage 3: Weather ===")
    backfill_historical_weather(start_year=2015, end_year=2020)


def stage_4_weekly_stats():
    """
    EXPENSIVE (time, not API cost) - ~45 calls/year x 6 years = ~270
    calls, but each year takes several minutes of wall-clock time based
    on tonight's original 6-year run. Expect this alone to take a while.
    """
    print("=== Stage 4: Weekly point-in-time stats (team/advanced/Elo) ===")
    backfill_weekly_stats(start_year=2015, end_year=2020)


def stage_5_player_data():
    """
    MOST expensive stage - rosters alone are a per-team loop (~686 teams
    x 6 years, same pattern as the original 35-45 minute roster
    backfill). Budget real time for this stage specifically.
    """
    print("=== Stage 5: Player rosters (SLOW - expect 30-45+ min) ===")
    backfill_rosters(start_year=2015, end_year=2020)

    print("\n=== Stage 5: Player season stats ===")
    backfill_player_stats(start_year=2015, end_year=2020)

    print("\n=== Stage 5: Player usage ===")
    backfill_player_usage(start_year=2015, end_year=2020)

    print("\n=== Stage 5: Offensive returning production ===")
    backfill_returning_production(start_year=2015, end_year=2020)


def stage_6_calculated_tables():
    """Free - pure DB computation, re-run after all raw data above exists."""
    print("=== Stage 6: Defensive returning production (calculated) ===")
    calc_defensive_returning_production()

    print("\n=== Stage 6: Coach tendencies (calculated) ===")
    calc_coach_tendencies()


if __name__ == "__main__":
    print("Run stages individually, e.g.:")
    print("  python -c \"from backfill_to_2015 import stage_1_teams_and_games; stage_1_teams_and_games()\"")