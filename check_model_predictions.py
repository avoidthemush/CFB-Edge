from app.db import SessionLocal
from app.models import ModelPrediction, BettingSystem, Game

db = SessionLocal()

rows = db.query(ModelPrediction).join(BettingSystem).join(Game).all()
print(f"Total prediction rows: {len(rows)}\n")

for r in rows:
    system = db.query(BettingSystem).filter(BettingSystem.id == r.system_id).first()
    game = db.query(Game).filter(Game.id == r.game_id).first()
    print(f"{game.away_team_name} @ {game.home_team_name} | {system.system_name} | "
          f"confidence={r.confidence:.1%} | bet_on_home={r.bet_on_home}")

db.close()