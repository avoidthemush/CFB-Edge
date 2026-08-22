"""
One-time cleanup: removes model_predictions rows for games OUTSIDE the
current week - leftover writes from before refresh_game_feature_cache.py's
stale-row pruning bug was fixed. Confirms what it's about to delete
before doing so, same discipline as every destructive operation tonight.
"""
from app.db import SessionLocal
from app.models import ModelPrediction, Game
from app.config import CURRENT_SEASON

db = SessionLocal()

current_week_game = db.query(Game).filter(
    Game.season == CURRENT_SEASON, Game.completed == False
).order_by(Game.week).first()
current_week = current_week_game.week if current_week_game else 1

stale = (
    db.query(ModelPrediction)
    .join(Game, ModelPrediction.game_id == Game.id)
    .filter(Game.season == CURRENT_SEASON, Game.week != current_week)
    .all()
)

print(f"Current week: {current_week}")
print(f"Found {len(stale)} stale prediction rows for other weeks:")
for row in stale:
    game = db.query(Game).filter(Game.id == row.game_id).first()
    print(f"  wk{game.week}: {game.away_team_name} @ {game.home_team_name} ({row.bet_type})")

confirm = input("\nDelete these rows? (yes/no): ")
if confirm.strip().lower() == "yes":
    for row in stale:
        db.delete(row)
    db.commit()
    print(f"Deleted {len(stale)} stale rows.")
else:
    print("Cancelled - nothing deleted.")

db.close()