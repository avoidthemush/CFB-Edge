from app.db import SessionLocal
from app.models import Team
from app.features.build_team_features import build_team_features

db = SessionLocal()
alabama = db.query(Team).filter(Team.school == "Alabama").first()

print("=== Alabama, 2025, Week 1 (should be 100% prior-season baseline) ===")
f1 = build_team_features(alabama.id, 2025, 1, db=db)
for k, v in f1.items():
    print(f"  {k}: {v}")

print("\n=== Alabama, 2025, Week 10 (should be fully current-season) ===")
f10 = build_team_features(alabama.id, 2025, 10, db=db)
for k, v in f10.items():
    print(f"  {k}: {v}")

print("\n=== Alabama, 2024, Week 1 (DeBoer's first year - should show is_new_coach_year=True) ===")
f_new_coach = build_team_features(alabama.id, 2024, 1, db=db)
for k, v in f_new_coach.items():
    print(f"  {k}: {v}")

db.close()