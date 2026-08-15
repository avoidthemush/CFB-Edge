from app.db import SessionLocal
from app.models import Team

db = SessionLocal()

# Known recent FBS transitions - should all show division='fbs'
recent_transitions = ["Jacksonville State", "Sam Houston", "Sacramento State", "North Dakota State"]

for name in recent_transitions:
    team = db.query(Team).filter(Team.school == name).first()
    if team:
        print(f"{name}: division={team.division}")
    else:
        print(f"{name}: NOT FOUND")

db.close()