import os
import httpx
from dotenv import load_dotenv
import json

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds"
params = {
    "apiKey": ODDS_API_KEY,
    "regions": "us",
    "markets": "h2h,spreads,totals",
    "bookmakers": "draftkings,fanduel",
}
resp = httpx.get(url, params=params, timeout=20)
events = resp.json()

# Find the North Carolina @ TCU game specifically
for event in events:
    if "TCU" in event.get("home_team", "") or "TCU" in event.get("away_team", ""):
        print(json.dumps(event, indent=2))
        break