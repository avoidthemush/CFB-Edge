from app.db import SessionLocal
from app.models import Player
from sqlalchemy import and_

db = SessionLocal()

# Step 1: identify sparse records
sparse_players = db.query(Player).filter(
    and_(
        Player.position.is_(None),
        Player.height.is_(None),
        Player.weight.is_(None),
        Player.home_city.is_(None),
    )
).all()

deleted = 0
flagged = 0

for sp in sparse_players:
    complete_match = db.query(Player).filter(
        Player.name == sp.name,
        Player.team_id == sp.team_id,
        Player.id != sp.id,
        Player.position.isnot(None),
    ).first()

    if complete_match:
        # True duplicate - the complete record already has this player
        db.delete(sp)
        deleted += 1
    else:
        # Standalone - real player, just thin CFBD data. Keep, flag it.
        sp.has_complete_bio = False
        flagged += 1

db.commit()
db.close()

print(f"Deleted {deleted} true duplicate sparse records")
print(f"Flagged {flagged} standalone sparse records as has_complete_bio=False")