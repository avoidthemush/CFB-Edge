from app.db import SessionLocal
from app.models import PollRanking, Team

db = SessionLocal()

rows = db.query(PollRanking).filter(PollRanking.year == 2026).order_by(PollRanking.rank).all()
print(f"Total 2026 rows: {len(rows)}")

if rows:
    print(f"Poll name: {rows[0].poll}")
    print(f"Week: {rows[0].week}")
    print("\nTop 5:")
    for r in rows[:5]:
        team = db.query(Team).filter(Team.id == r.team_id).first()
        print(f"  #{r.rank} {team.school} - {r.points} pts")

db.close()