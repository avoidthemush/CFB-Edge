import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
with cfbd.ApiClient(configuration) as api_client:
    games_api = cfbd.GamesApi(api_client)
    results = games_api.get_weather(year=2025)
    print(f"Bulk call (no team filter) - rows returned: {len(results)}")