from app.db import SessionLocal
from app.models import Player, Team

db = SessionLocal()

team = db.query(Team).filter(Team.school == "Clark Atlanta").first()
print(f"Team: {team.school} (id={team.id}, verified={team.is_verified})")

players = db.query(Player).filter(Player.team_id == team.id).all()
print(f"\nAll {len(players)} players:")
for p in players:
    print(f"  {p.name} ({p.position}, class {p.class_year})")

db.close()