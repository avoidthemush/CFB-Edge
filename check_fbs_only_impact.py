from app.db import SessionLocal
from app.models import Game, Team

db = SessionLocal()

all_games = db.query(Game).filter(
    Game.season >= 2021, Game.season <= 2024, Game.completed == True
).all()

fbs_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}

fbs_vs_fbs = [g for g in all_games if g.home_team_id in fbs_ids and g.away_team_id in fbs_ids]

print(f"Total completed games (2021-2024): {len(all_games)}")
print(f"FBS vs FBS only: {len(fbs_vs_fbs)} ({len(fbs_vs_fbs)/len(all_games)*100:.1f}% of total)")

from app.models import CFBDBettingLine
fbs_game_ids = {g.id for g in fbs_vs_fbs}
lines_for_fbs = db.query(CFBDBettingLine.game_id).filter(
    CFBDBettingLine.game_id.in_(fbs_game_ids)
).distinct().count()
print(f"\nOf FBS-vs-FBS games, how many have a market line: {lines_for_fbs}/{len(fbs_vs_fbs)} "
      f"({lines_for_fbs/len(fbs_vs_fbs)*100:.1f}%)")

db.close()