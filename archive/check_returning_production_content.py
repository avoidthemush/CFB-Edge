import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)

with cfbd.ApiClient(configuration) as api_client:
    players_api = cfbd.PlayersApi(api_client)

    for year in [2013, 2015, 2019, 2021]:
        result = players_api.get_returning_production(year=year, team="Alabama")
        print(f"\nYear {year}: {len(result)} row(s)")
        for r in result:
            print(f"  {r.to_dict() if hasattr(r, 'to_dict') else r}")