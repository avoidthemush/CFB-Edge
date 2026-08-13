from app.db import SessionLocal
from app.models import CoachSeason, Team, Coach, Game

db = SessionLocal()

game = db.query(Game).filter(Game.id == 401762522).first()
print(f"Game: {game.away_team_name} @ {game.home_team_name}, {game.season} week {game.week}")

for team_id, label in [(game.home_team_id, "home"), (game.away_team_id, "away")]:
    team = db.query(Team).filter(Team.id == team_id).first()
    print(f"\n{label} team: {team.school}")

    for year in [game.season - 1, game.season]:
        rows = db.query(CoachSeason).filter(
            CoachSeason.team_id == team_id, CoachSeason.year == year
        ).all()
        print(f"  {year}: {len(rows)} coach_season row(s)")
        for r in rows:
            coach = db.query(Coach).filter(Coach.id == r.coach_id).first()
            print(f"    coach_id={r.coach_id} ({coach.first_name} {coach.last_name}), wins={r.wins}, losses={r.losses}")

db.close()