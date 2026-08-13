import csv
from app.db import SessionLocal
from app.models import Game, Team

with open("training_data_validation.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

null_2023 = [r for r in rows if r["season"] == "2023" and r["diff_sp+_rating"] in (None, "", "None")]

db = SessionLocal()

for r in null_2023:
    game = db.query(Game).filter(Game.id == int(r["game_id"])).first()
    if game is None:
        continue
    home = db.query(Team).filter(Team.id == game.home_team_id).first()
    away = db.query(Team).filter(Team.id == game.away_team_id).first()

    if home.division == "fbs" and away.division == "fbs":
        print(f"{away.school} (div={away.division}) @ {home.school} (div={home.division}), "
              f"season={game.season}, week={game.week}")

db.close()