import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
with cfbd.ApiClient(configuration) as api_client:
    stats_api = cfbd.StatsApi(api_client)
    results = stats_api.get_player_season_stats(year=2025)

    teams = set(r.team for r in results)
    print(f"Total rows returned: {len(results)}")
    print(f"Distinct teams represented: {len(teams)}")