import os
import httpx
from dotenv import load_dotenv

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_ncaaf/events"
params = {
    "apiKey": ODDS_API_KEY,
    "date": "2025-10-15T12:00:00Z",  # same date as our earlier successful odds test
}

resp = httpx.get(url, params=params, timeout=20)
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
else:
    print("\nUnexpected response shape:")
    print(str(data)[:1000])