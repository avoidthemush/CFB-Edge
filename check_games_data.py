from app.db import SessionLocal
from app.models import Game

db = SessionLocal()

for year in [2021, 2025, 2026]:
    total = db.query(Game).filter(Game.season == year).count()
    completed = db.query(Game).filter(Game.season == year, Game.completed == True).count()
    print(f"{year}: {total} games, {completed} completed")

sample = db.query(Game).filter(Game.season == 2025, Game.completed == True).first()
if sample:
    print(f"\nSample: {sample.away_team_name} @ {sample.home_team_name} - {sample.away_points}-{sample.home_points}")

db.close()