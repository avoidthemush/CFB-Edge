from app.db import SessionLocal
from app.models import TeamSeasonStat, Team
from sqlalchemy import func

db = SessionLocal()

categories = db.query(TeamSeasonStat.category).filter(
    TeamSeasonStat.year == 2025
).distinct().order_by(TeamSeasonStat.category).all()

print(f"Total distinct categories: {len(categories)}")
for (c,) in categories:
    print(f"  {c}")

print("\n=== Sample: Alabama 2025 turnover-related stats ===")
alabama = db.query(Team).filter(Team.school == "Alabama").first()
turnover_related = db.query(TeamSeasonStat).filter(
    TeamSeasonStat.team_id == alabama.id,
    TeamSeasonStat.year == 2025,
    TeamSeasonStat.category.ilike("%fumble%") | TeamSeasonStat.category.ilike("%interception%")
).all()
for row in turnover_related:
    print(f"  {row.category}: {row.stat_value}")

db.close()