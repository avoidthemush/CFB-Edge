"""
Sanity test: runs predict_week.py's mechanics against a REAL, COMPLETED
2025 game, ignoring the known outcome, purely to confirm the live
prediction pipeline works end-to-end before ever pointing it at true
2026 data (which likely doesn't have posted lines yet, season hasn't
started).
"""
from app.db import SessionLocal
from app.models_ml.predict_week import load_production_model, predict_game
from app.models import Game

db = SessionLocal()
model, scaler, imputer, feature_cols = load_production_model()

sample_game = db.query(Game).filter(
    Game.season == 2025, Game.week == 5, Game.completed == True,
).first()

if sample_game:
    result = predict_game(sample_game.id, model, scaler, imputer, feature_cols, db)
    print(f"{sample_game.away_team_name} @ {sample_game.home_team_name}")
    print(f"Actual result: {sample_game.away_points}-{sample_game.home_points}")
    print(f"\nModel output: {result}")
else:
    print("No week 5 2025 game found")

db.close()