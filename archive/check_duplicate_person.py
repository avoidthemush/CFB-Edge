from app.db import SessionLocal
from app.models import Player

db = SessionLocal()

dupes = db.query(Player).filter(Player.name == "Shilo Sanders").all()
for p in dupes:
    print(f"ID {p.id}: {p.name}, {p.position}, class {p.class_year}, "
          f"{p.height}in/{p.weight}lb, {p.home_city}, {p.home_state}, team_id={p.team_id}")

db.close()