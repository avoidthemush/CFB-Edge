from app.db import SessionLocal
from app.models import CoachTendency, Coach, CoachSeason

db = SessionLocal()

print("=== Range sanity check ===")
total = db.query(CoachTendency).count()
out_of_range_rates = db.query(CoachTendency).filter(
    (CoachTendency.pass_rate < 0) | (CoachTendency.pass_rate > 1)
).count()
print(f"Total rows: {total}")
print(f"pass_rate out of [0,1]: {out_of_range_rates}")

print("\n=== seasons_used distribution ===")
from sqlalchemy import func
dist = db.query(CoachTendency.seasons_used, func.count(CoachTendency.id)).group_by(
    CoachTendency.seasons_used
).order_by(CoachTendency.seasons_used).all()
for seasons, count in dist:
    print(f"  {seasons} prior season(s) used: {count} coach-year rows")

print("\n=== Sample: a coach with multiple prior seasons ===")
multi_season = db.query(CoachTendency).filter(CoachTendency.seasons_used >= 3).first()
if multi_season:
    coach = db.query(Coach).filter(Coach.id == multi_season.coach_id).first()
    print(f"  {coach.first_name} {coach.last_name}, as of {multi_season.as_of_year} "
          f"({multi_season.seasons_used} prior seasons)")
    print(f"  pass_rate: {multi_season.pass_rate}")
    print(f"  off_success_rate: {multi_season.off_success_rate}")
    print(f"  off_explosiveness: {multi_season.off_explosiveness}")
    print(f"  def_havoc_rate: {multi_season.def_havoc_rate}")
    print(f"  def_points_per_opportunity: {multi_season.def_points_per_opportunity}")

    print("\n  Their actual coach_seasons on record:")
    seasons = db.query(CoachSeason).filter(
        CoachSeason.coach_id == multi_season.coach_id,
        CoachSeason.year < multi_season.as_of_year
    ).order_by(CoachSeason.year).all()
    for s in seasons:
        print(f"    {s.year}: {s.wins}-{s.losses}, SP+ overall {s.sp_overall}")

db.close()