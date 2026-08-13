from app.db import SessionLocal
from app.models import Player, Team
from sqlalchemy import and_, func

db = SessionLocal()

sparse_by_team = (
    db.query(Team.school, func.count(Player.id))
    .join(Player, Player.team_id == Team.id)
    .filter(
        and_(
            Player.position.is_(None),
            Player.height.is_(None),
            Player.home_city.is_(None),
        )
    )
    .group_by(Team.school)
    .order_by(func.count(Player.id).desc())
    .limit(20)
    .all()
)

print("Teams with the most sparse records:")
for school, count in sparse_by_team:
    total_for_team = db.query(Player).filter(Player.team_id == db.query(Team.id).filter(Team.school == school).scalar()).count()
    print(f"  {school}: {count} sparse / {total_for_team} total")

db.close()