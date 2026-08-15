from app.db import SessionLocal
from app.models import Game

db = SessionLocal()
week_zero_count = db.query(Game).filter(Game.week == 0).count()
print(f"Games with week=0: {week_zero_count}")

min_week = db.query(Game.week).order_by(Game.week).first()
print(f"Lowest week value in database: {min_week[0] if min_week else 'none found'}")
db.close()