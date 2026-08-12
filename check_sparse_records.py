from app.db import SessionLocal
from app.models import Player
from sqlalchemy import and_

db = SessionLocal()

total = db.query(Player).count()

sparse = db.query(Player).filter(
    and_(
        Player.position.is_(None),
        Player.height.is_(None),
        Player.weight.is_(None),
        Player.home_city.is_(None),
    )
).count()

print(f"Total players: {total}")
print(f"Sparse records (no position/height/weight/hometown): {sparse} ({sparse/total*100:.1f}%)")

print("\nclass_year values on sparse records (checking for the 'calendar year' pattern):")
sparse_years = db.query(Player.class_year).filter(
    and_(Player.position.is_(None), Player.height.is_(None), Player.home_city.is_(None))
).distinct().limit(20).all()
for (y,) in sparse_years:
    print(f"  {y}")

print("\nclass_year values on COMPLETE records (position + height both present):")
complete_years = db.query(Player.class_year).filter(
    Player.position.isnot(None), Player.height.isnot(None)
).distinct().limit(20).all()
for (y,) in complete_years:
    print(f"  {y}")

db.close()