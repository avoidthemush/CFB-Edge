import csv
from collections import Counter

from app.db import SessionLocal
from app.models import Game, Team

with open("training_data_validation.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

null_2023 = [r for r in rows if r["season"] == "2023" and r["diff_sp+_rating"] in (None, "", "None")]
print(f"2023 null diff_sp+_rating rows: {len(null_2023)}")

db = SessionLocal()

fbs_vs_fbs_nulls = 0
involves_nonfbs = 0
sample_fbs_vs_fbs = []

for r in null_2023:
    game = db.query(Game).filter(Game.id == int(r["game_id"])).first()
    if game is None:
        continue
    home = db.query(Team).filter(Team.id == game.home_team_id).first()
    away = db.query(Team).filter(Team.id == game.away_team_id).first()

    home_fbs = home and home.division == "fbs"
    away_fbs = away and away.division == "fbs"

    if home_fbs and away_fbs:
        fbs_vs_fbs_nulls += 1
        if len(sample_fbs_vs_fbs) < 5:
            sample_fbs_vs_fbs.append(f"{away.school} @ {home.school}")
    else:
        involves_nonfbs += 1

db.close()

print(f"\nOf those nulls:")
print(f"  FBS vs FBS (unexpected - real problem): {fbs_vs_fbs_nulls}")
print(f"  Involves a non-FBS team (expected): {involves_nonfbs}")
print(f"\nSample FBS-vs-FBS null games (if any):")
for s in sample_fbs_vs_fbs:
    print(f"  {s}")