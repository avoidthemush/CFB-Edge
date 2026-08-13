from app.db import SessionLocal
from app.models import TeamStatWeekly, TeamAdvancedStatWeekly, RatingSnapshot, Team
from sqlalchemy import func

db = SessionLocal()

print("=== Team stats weekly: rows per week ===")
by_week = db.query(TeamStatWeekly.through_week, func.count(TeamStatWeekly.id)).filter(
    TeamStatWeekly.year == 2025
).group_by(TeamStatWeekly.through_week).order_by(TeamStatWeekly.through_week).all()
for week, count in by_week:
    print(f"  Week {week}: {count} rows")

print("\n=== Advanced stats weekly: rows per week ===")
by_week_adv = db.query(TeamAdvancedStatWeekly.through_week, func.count(TeamAdvancedStatWeekly.id)).filter(
    TeamAdvancedStatWeekly.year == 2025
).group_by(TeamAdvancedStatWeekly.through_week).order_by(TeamAdvancedStatWeekly.through_week).all()
for week, count in by_week_adv:
    print(f"  Week {week}: {count} rows")

print("\n=== Elo weekly: rows per week ===")
by_week_elo = db.query(RatingSnapshot.week, func.count(RatingSnapshot.id)).filter(
    RatingSnapshot.year == 2025, RatingSnapshot.system == "elo", RatingSnapshot.week.isnot(None)
).group_by(RatingSnapshot.week).order_by(RatingSnapshot.week).all()
for week, count in by_week_elo:
    print(f"  Week {week}: {count} rows")

print("\n=== Sample: Alabama, team_stats_weekly, a few weeks ===")
alabama = db.query(Team).filter(Team.school == "Alabama").first()
samples = db.query(TeamStatWeekly).filter(
    TeamStatWeekly.team_id == alabama.id, TeamStatWeekly.year == 2025,
    TeamStatWeekly.category == "totalYards"
).order_by(TeamStatWeekly.through_week).all()
for s in samples:
    print(f"  Through week {s.through_week}: totalYards = {s.stat_value}")

db.close()