from app.db import SessionLocal
from app.models import Game, Team
from app.features.build_game_features import build_game_features

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
game = db.query(Game).filter(
    (Game.home_team_id == alabama.id) | (Game.away_team_id == alabama.id),
    Game.season == 2025, Game.completed == True,
).order_by(Game.week).first()

print(f"Game: {game.away_team_name} @ {game.home_team_name}, week {game.week}, {game.season}")
print(f"Actual score: {game.away_points} - {game.home_points}\n")

features = build_game_features(game.id, db=db)
for k, v in features.items():
    print(f"  {k}: {v}")

db.close()