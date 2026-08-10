import os
from dotenv import load_dotenv
import httpx
import cfbd

load_dotenv()

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def test_cfbd():
    print("Testing CFBD...")
    try:
        configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
        with cfbd.ApiClient(configuration) as api_client:
            api_instance = cfbd.TeamsApi(api_client)
            teams = api_instance.get_teams(year=2025)
            print(f"  OK - pulled {len(teams)} teams. Example: {teams[0].school}")
    except Exception as e:
        print(f"  FAILED: {e}")


def test_odds_api():
    print("Testing The Odds API...")
    try:
        url = "https://api.the-odds-api.com/v4/sports"
        resp = httpx.get(url, params={"apiKey": ODDS_API_KEY}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"  OK - {len(data)} sports returned.")
        remaining = resp.headers.get("x-requests-remaining")
        used = resp.headers.get("x-requests-used")
        print(f"  Quota - used: {used}, remaining: {remaining}")
    except Exception as e:
        print(f"  FAILED: {e}")


def test_openweather():
    print("Testing OpenWeather...")
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": "Tuscaloosa,AL,US", "appid": OPENWEATHER_API_KEY, "units": "imperial"}
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        temp = data["main"]["temp"]
        condition = data["weather"][0]["main"]
        print(f"  OK - Tuscaloosa, AL: {temp}F, {condition}")
    except Exception as e:
        print(f"  FAILED: {e}")


if __name__ == "__main__":
    test_cfbd()
    test_odds_api()
    test_openweather()