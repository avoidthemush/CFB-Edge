from app.db import SessionLocal
from app.models import Game, CFBDBettingLine, Team

db = SessionLocal()

# Find a game where the HOME team was the heavy favorite - opposite case from FSU/Alabama
alabama = db.query(Team).filter(Team.school == "Alabama").first()
home_favorite_game = db.query(Game).filter(
    Game.home_team_id == alabama.id, Game.season == 2025, Game.completed == True,
).order_by(Game.week).first()

line = db.query(CFBDBettingLine).filter(
    CFBDBettingLine.game_id == home_favorite_game.id, CFBDBettingLine.provider == "Bovada"
).first()

print(f"{home_favorite_game.away_team_name} @ {home_favorite_game.home_team_name} (home = Alabama, likely favorite)")
print(f"  spread field value: {line.spread if line else 'no Bovada line'}")
print(f"  actual: {home_favorite_game.away_points} - {home_favorite_game.home_points}")
print(f"  actual_spread (home-away): {home_favorite_game.home_points - home_favorite_game.away_points}")

db.close()