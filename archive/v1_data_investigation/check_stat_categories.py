import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
with cfbd.ApiClient(configuration) as api_client:
    stats_api = cfbd.StatsApi(api_client)
    results = stats_api.get_player_season_stats(year=2025, team="Alabama")

    categories = sorted(set((r.category, r.stat_type) for r in results))
    print(f"Total stat rows: {len(results)}\n")
    print("Distinct (category, statType) pairs:")
    for cat, stat_type in categories:
        print(f"  {cat} / {stat_type}")

    print("\nSample defensive-looking rows:")
    for r in results[:5]:
        print(f"  {r.player} ({r.position}) - {r.category}/{r.stat_type}: {r.stat}")