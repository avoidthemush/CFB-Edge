import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Game, Team

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()

with cfbd.ApiClient(configuration) as api_client:
    games_api = cfbd.GamesApi(api_client)
    results = games_api.get_weather(year=2025, team="Alabama")

    print(f"Rows returned for Alabama 2025: {len(results)}")

    for w in results[:3]:
        print("\n--- Raw weather object ---")
        print(w.to_dict() if hasattr(w, "to_dict") else w)

    if results:
        sample_id = getattr(results[0], "id", None)
        print(f"\nSample weather row's game id: {sample_id} (type: {type(sample_id)})")

        our_game = db.query(Game).filter(Game.id == sample_id).first()
        print(f"Matches a row in our games table: {our_game is not None}")
        if our_game:
            print(f"  {our_game.away_team_name} @ {our_game.home_team_name}, week {our_game.week}")

db.close()