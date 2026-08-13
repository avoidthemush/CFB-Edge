from app.db import SessionLocal
from app.models import (
    Game, Team, Venue, CFBDBettingLine, RatingSnapshot, TeamAdvancedStat,
    OffensiveReturningProduction, DefensiveReturningProduction,
)

db = SessionLocal()

# Pick a spread of real games: different years, different program sizes
sample_criteria = [
    ("Alabama", 2023),
    ("Alabama", 2025),
    ("Boise State", 2022),
    ("Toledo", 2024),
    ("Sacramento State", 2026),  # newest FBS addition
]

for school, year in sample_criteria:
    print(f"\n{'='*60}")
    print(f"{school} - {year}")
    print('='*60)

    team = db.query(Team).filter(Team.school == school).first()
    if not team:
        print(f"  TEAM NOT FOUND")
        continue

    game = db.query(Game).filter(
        (Game.home_team_id == team.id) | (Game.away_team_id == team.id),
        Game.season == year,
    ).first()

    if not game:
        print(f"  NO GAME FOUND for {year}")
        continue

    print(f"  Game: {game.away_team_name} @ {game.home_team_name}, week {game.week}")

    venue = db.query(Venue).filter(Venue.id == game.venue_id).first()
    print(f"  Venue: {venue.name if venue else 'MISSING'} "
          f"({'has coords' if venue and venue.latitude else 'NO COORDS'})")

    lines = db.query(CFBDBettingLine).filter(CFBDBettingLine.game_id == game.id).count()
    print(f"  Betting lines: {lines} provider row(s)")

    rating = db.query(RatingSnapshot).filter(
        RatingSnapshot.team_id == team.id, RatingSnapshot.year == year, RatingSnapshot.system == "sp+"
    ).first()
    print(f"  SP+ rating: {rating.rating if rating else 'MISSING'}")

    adv = db.query(TeamAdvancedStat).filter(
        TeamAdvancedStat.team_id == team.id, TeamAdvancedStat.year == year
    ).first()
    print(f"  Advanced stats: {'present' if adv else 'MISSING'}")

    off_rp = db.query(OffensiveReturningProduction).filter(
        OffensiveReturningProduction.team_id == team.id, OffensiveReturningProduction.year == year
    ).first()
    print(f"  Offensive returning production: {off_rp.percent_ppa if off_rp else 'MISSING'}")

    def_rp = db.query(DefensiveReturningProduction).filter(
        DefensiveReturningProduction.team_id == team.id, DefensiveReturningProduction.year == year
    ).first()
    print(f"  Defensive returning production: "
          f"{def_rp.percent_havoc_returning if def_rp else 'MISSING'}")

db.close()