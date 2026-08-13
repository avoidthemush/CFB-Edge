from app.db import SessionLocal
from app.models import Player, Team

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
players = db.query(Player).filter(Player.team_id == alabama.id).limit(5).all()

print(f"Sample players for Alabama:")
for p in players:
    print(f"  {p.name} ({p.position}, class {p.class_year}) - {p.home_city}, {p.home_state} - {p.height}in/{p.weight}lb")

total = db.query(Player).filter(Player.team_id == alabama.id).count()
print(f"\nTotal Alabama players in DB: {total}")

db.close()