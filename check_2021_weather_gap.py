from app.db import SessionLocal
from app.models import Game, WeatherSnapshot

db = SessionLocal()

total_2021_games = db.query(Game).filter(Game.season == 2021).count()
games_with_weather = db.query(WeatherSnapshot).join(
    Game, Game.id == WeatherSnapshot.game_id
).filter(Game.season == 2021).count()

print(f"Total 2021 games: {total_2021_games}")
print(f"2021 games with weather: {games_with_weather}")

# Check if it's concentrated in certain weeks
from sqlalchemy import func
by_week = db.query(Game.week, func.count(WeatherSnapshot.id)).join(
    WeatherSnapshot, WeatherSnapshot.game_id == Game.id, isouter=True
).filter(Game.season == 2021).group_by(Game.week).order_by(Game.week).all()

print("\nGames with weather by week (2021):")
for week, count in by_week:
    total_that_week = db.query(Game).filter(Game.season == 2021, Game.week == week).count()
    print(f"  Week {week}: {count} with weather / {total_that_week} total games")

db.close()