from app.db import SessionLocal
from app.models import Player
from sqlalchemy import and_

db = SessionLocal()

sparse_players = db.query(Player).filter(
    and_(
        Player.position.is_(None),
        Player.height.is_(None),
        Player.weight.is_(None),
        Player.home_city.is_(None),
    )
).all()

has_complete_duplicate = 0
standalone_sparse = 0

for sp in sparse_players:
    complete_match = db.query(Player).filter(
        Player.name == sp.name,
        Player.team_id == sp.team_id,
        Player.id != sp.id,
        Player.position.isnot(None),
    ).first()

    if complete_match:
        has_complete_duplicate += 1
    else:
        standalone_sparse += 1

print(f"Sparse records that duplicate a complete record: {has_complete_duplicate}")
print(f"Sparse records with NO complete counterpart (standalone): {standalone_sparse}")

db.close()