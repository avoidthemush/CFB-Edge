import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
with cfbd.ApiClient(configuration) as api_client:
    players_api = cfbd.PlayersApi(api_client)
    results = players_api.get_player_usage(year=2025)

    from collections import defaultdict
    by_position = defaultdict(list)
    for r in results:
        overall = r.usage.overall if r.usage else None
        by_position[r.position].append(overall)

    print(f"{'Position':<10} {'Count':>7} {'Non-null':>9} {'Avg (non-null)':>16}")
    for pos in sorted(by_position.keys()):
        vals = by_position[pos]
        non_null = [v for v in vals if v is not None]
        avg = sum(non_null) / len(non_null) if non_null else 0
        print(f"{pos:<10} {len(vals):>7} {len(non_null):>9} {avg:>16.3f}")