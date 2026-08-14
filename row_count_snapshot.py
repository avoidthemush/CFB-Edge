from app.db import SessionLocal
from app.models import (
    Team, Venue, Coach, CoachSeason, Game, OddsSnapshot, CFBDBettingLine,
    WeatherSnapshot, TeamSeasonStat, TeamAdvancedStat, RatingSnapshot,
    TeamATS, TeamTalent, RecruitingClass, OffensiveReturningProduction,
    DefensiveReturningProduction, TransferPortalEntry, PollRanking,
    TeamSourceAlias, Player, PlayerSeasonStat, TeamStatWeekly,
    TeamAdvancedStatWeekly, CoachTendency,
)

db = SessionLocal()

tables = [
    ("teams", Team), ("venues", Venue), ("coaches", Coach), ("coach_seasons", CoachSeason),
    ("games", Game), ("odds_snapshots", OddsSnapshot), ("cfbd_betting_lines", CFBDBettingLine),
    ("weather_snapshots", WeatherSnapshot), ("team_season_stats", TeamSeasonStat),
    ("team_advanced_stats", TeamAdvancedStat), ("rating_snapshots", RatingSnapshot),
    ("team_ats", TeamATS), ("team_talent", TeamTalent), ("recruiting_classes", RecruitingClass),
    ("offensive_returning_production", OffensiveReturningProduction),
    ("defensive_returning_production", DefensiveReturningProduction),
    ("transfer_portal_entries", TransferPortalEntry), ("poll_rankings", PollRanking),
    ("team_source_aliases", TeamSourceAlias), ("players", Player),
    ("player_season_stats", PlayerSeasonStat), ("team_stats_weekly", TeamStatWeekly),
    ("team_advanced_stats_weekly", TeamAdvancedStatWeekly), ("coach_tendencies", CoachTendency),
]

print(f"{'Table':<35} {'Rows':>10}")
print("-" * 46)
total = 0
for name, model in tables:
    count = db.query(model).count()
    total += count
    print(f"{name:<35} {count:>10,}")

print("-" * 46)
print(f"{'TOTAL':<35} {total:>10,}")

db.close()