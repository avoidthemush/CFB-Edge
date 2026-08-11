import os
import httpx
from dotenv import load_dotenv

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

url = "https://api.the-odds-api.com/v4/historical/sports/americanfootball_ncaaf/events"
params = {
    "apiKey": ODDS_API_KEY,
    "commenceTimeFrom": "2025-08-01T00:00:00Z",
    "commenceTimeTo": "2026-01-15T00:00:00Z",
    "date": "2026-01-15T00:00:00Z",  # snapshot pointer - querying as of season's end
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