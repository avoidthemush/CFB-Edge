"""
Spot-checks the new team_recent_form table - confirming real data
landed correctly, and specifically that the season-boundary requirement
worked (teams' last-10 should reach back into 2025's final games, since
2026 has no completed games yet).
"""
from app.db import SessionLocal
from app.models import Team, TeamRecentForm, Game

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
form = db.query(TeamRecentForm).filter(TeamRecentForm.team_id == alabama.id).first()

print(f"=== Alabama recent form ===")
print(f"Games counted: {form.games_counted}")
print(f"ATS: {form.ats_wins}-{form.ats_losses}-{form.ats_pushes}")
print(f"O/U: {form.ou_overs}-{form.ou_unders}-{form.ou_pushes}")
print(f"SU: {form.su_wins}-{form.su_losses}")

print(f"\n=== Confirming season-boundary crossing ===")
last_10 = db.query(Game).filter(
    (Game.home_team_id == alabama.id) | (Game.away_team_id == alabama.id),
    Game.completed == True, Game.home_points.isnot(None),
).order_by(Game.start_date.desc()).limit(10).all()

for g in last_10:
    print(f"  {g.season} wk{g.week}: {g.away_team_name} @ {g.home_team_name} "
          f"({g.away_points}-{g.home_points}) - {g.start_date.date()}")

db.close()