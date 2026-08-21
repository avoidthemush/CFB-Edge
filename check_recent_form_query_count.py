"""
Confirms whether the remaining ~48s cost is coming from the per-team
TeamRecentForm existence-check query still running inside the loop -
same per-item-query pattern already fixed twice tonight, possibly
present here too.
"""
import time
from app.db import SessionLocal
from app.models import Team, TeamRecentForm

db = SessionLocal()
teams = db.query(Team).filter(Team.division == "fbs").all()

t0 = time.time()
for team in teams:
    db.query(TeamRecentForm).filter(TeamRecentForm.team_id == team.id).first()
t1 = time.time()

print(f"138 individual TeamRecentForm lookups: {t1-t0:.2f}s ({(t1-t0)/len(teams)*1000:.0f}ms per team)")
db.close()