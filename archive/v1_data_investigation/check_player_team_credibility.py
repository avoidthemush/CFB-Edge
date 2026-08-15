from app.db import SessionLocal
from app.models import Player, Team

db = SessionLocal()

unverified_team_ids = {t.id for t in db.query(Team).filter(Team.is_verified == False).all()}
players_on_unverified = db.query(Player).filter(Player.team_id.in_(unverified_team_ids)).count()

print(f"Players linked to unverified/stub teams: {players_on_unverified}")

db.close()