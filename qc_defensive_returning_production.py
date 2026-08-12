from app.db import SessionLocal
from app.models import DefensiveReturningProduction, Team

db = SessionLocal()

print("=== Range check: percent_havoc_returning should be 0.0-1.0 ===")
out_of_range = db.query(DefensiveReturningProduction).filter(
    (DefensiveReturningProduction.percent_havoc_returning < 0) |
    (DefensiveReturningProduction.percent_havoc_returning > 1)
).count()
print(f"Out of range: {out_of_range}")

print("\n=== Null percent (total_havoc_prior_year was 0) ===")
null_pct = db.query(DefensiveReturningProduction).filter(
    DefensiveReturningProduction.percent_havoc_returning.is_(None)
).count()
print(f"Null: {null_pct}")

print("\n=== Sample: Alabama, most recent years ===")
alabama = db.query(Team).filter(Team.school == "Alabama").first()
rows = db.query(DefensiveReturningProduction).filter(
    DefensiveReturningProduction.team_id == alabama.id
).order_by(DefensiveReturningProduction.year).all()

for r in rows:
    print(f"  {r.year}: {r.players_returning_count}/{r.players_prior_year_count} players returning, "
          f"havoc {r.havoc_returning:.1f}/{r.total_havoc_prior_year:.1f} "
          f"({r.percent_havoc_returning*100:.1f}% returning)" if r.percent_havoc_returning is not None
          else f"  {r.year}: percent_havoc_returning is None")

print("\n=== Distribution check: average percent_havoc_returning across all teams/years ===")
all_pcts = [r.percent_havoc_returning for r in db.query(DefensiveReturningProduction).all() if r.percent_havoc_returning is not None]
if all_pcts:
    print(f"  Min: {min(all_pcts)*100:.1f}%")
    print(f"  Max: {max(all_pcts)*100:.1f}%")
    print(f"  Avg: {sum(all_pcts)/len(all_pcts)*100:.1f}%")

db.close()