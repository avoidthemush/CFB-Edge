from app.db import SessionLocal
from app.models import Player, PlayerSeasonStat

db = SessionLocal()

# Milroe should be on Alabama's roster for 2024 even before Week 1 games existed
milroe = db.query(Player).filter(Player.name == "Jalen Milroe").first()
if milroe:
    print(f"Player: {milroe.name}, current team_id in players table: {milroe.team_id}")

db.close()