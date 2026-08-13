import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
with cfbd.ApiClient(configuration) as api_client:
    players_api = cfbd.PlayersApi(api_client)
    results = players_api.get_player_usage(year=2025)

    teams = set(r.team for r in results)
    print(f"Total rows returned: {len(results)}")
    print(f"Distinct teams represented: {len(teams)}")