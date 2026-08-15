from app.db import SessionLocal
from app.models import ReturningProduction, Team

db = SessionLocal()

total = db.query(ReturningProduction).filter(ReturningProduction.year == 2025).count()
print(f"2025: {total} rows")

fields = [
    "total_ppa", "total_passing_ppa", "total_receiving_ppa", "total_rushing_ppa",
    "percent_ppa", "percent_passing_ppa", "percent_receiving_ppa", "percent_rushing_ppa",
    "usage", "passing_usage", "receiving_usage", "rushing_usage",
]

print("\nField completeness (2025):")
for field in fields:
    col = getattr(ReturningProduction, field)
    n = db.query(ReturningProduction).filter(ReturningProduction.year == 2025, col.isnot(None)).count()
    print(f"  {field}: {n}/{total}")

alabama = db.query(Team).filter(Team.school == "Alabama").first()
sample = db.query(ReturningProduction).filter(
    ReturningProduction.team_id == alabama.id, ReturningProduction.year == 2025
).first()
if sample:
    print(f"\nAlabama 2025: percent_ppa={sample.percent_ppa}, usage={sample.usage}")

db.close()