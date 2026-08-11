import os
import httpx
from dotenv import load_dotenv

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Mid-2025 regular season - a date well into the season when most FBS
# matchups would have had lines posted
TEST_DATE = "2025-10-15T12:00:00Z"

url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_ncaaf/odds"
params = {
    "apiKey": ODDS_API_KEY,
    "regions": "us",
    "markets": "h2h",  # cheapest single market, just to test cost/structure
    "date": TEST_DATE,
}

resp = httpx.get(url, params=params, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Requests used: {resp.headers.get('x-requests-used')}")
print(f"Requests remaining: {resp.headers.get('x-requests-remaining')}")
print(f"Requests last cost: {resp.headers.get('x-requests-last')}")

data = resp.json()
if isinstance(data, dict) and "data" in data:
    events = data["data"]
    names = set()
    for e in events:
        names.add(e.get("home_team"))
        names.add(e.get("away_team"))
    print(f"\nEvents returned: {len(events)}")
    print(f"Unique team names: {len(names)}")
    print(f"Snapshot timestamp: {data.get('timestamp')}")
else:
    print("\nUnexpected response shape:")
    print(data)