from app.db import SessionLocal
from app.models import RatingSnapshot
from sqlalchemy import func

db = SessionLocal()

print("Rows per system:")
systems = db.query(
    RatingSnapshot.system, func.count(RatingSnapshot.id)
).group_by(RatingSnapshot.system).all()
for system, count in systems:
    print(f"  {system}: {count}")

print("\nField completeness by system:")
for (system,) in db.query(RatingSnapshot.system).distinct().all():
    rows = db.query(RatingSnapshot).filter(RatingSnapshot.system == system)
    total = rows.count()
    rating_pct = rows.filter(RatingSnapshot.rating.isnot(None)).count() / total * 100 if total else 0
    off_pct = rows.filter(RatingSnapshot.offense_rating.isnot(None)).count() / total * 100 if total else 0
    def_pct = rows.filter(RatingSnapshot.defense_rating.isnot(None)).count() / total * 100 if total else 0
    print(f"  {system}: rating={rating_pct:.0f}%, offense={off_pct:.0f}%, defense={def_pct:.0f}%")

print("\nSample rows (one per system):")
for (system,) in db.query(RatingSnapshot.system).distinct().all():
    sample = db.query(RatingSnapshot).filter(
        RatingSnapshot.system == system, RatingSnapshot.year == 2025
    ).first()
    if sample:
        print(f"  [{system}] team_id={sample.team_id}, rating={sample.rating}, "
              f"off={sample.offense_rating}, def={sample.defense_rating}")

db.close()