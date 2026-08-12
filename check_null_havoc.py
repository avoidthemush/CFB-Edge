from app.db import SessionLocal
from app.models import DefensiveReturningProduction, Team

db = SessionLocal()

nulls = db.query(DefensiveReturningProduction).filter(
    DefensiveReturningProduction.percent_havoc_returning.is_(None)
).all()

print(f"Total null rows: {len(nulls)}")
print("\nSample (team, year, total_havoc_prior_year):")
for row in nulls[:10]:
    team = db.query(Team).filter(Team.id == row.team_id).first()
    print(f"  {team.school} ({row.year}): total_havoc_prior_year={row.total_havoc_prior_year}, "
          f"players_prior_year_count={row.players_prior_year_count}")

db.close()