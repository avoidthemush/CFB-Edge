import os
import time
import cfbd
import httpx
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

from app.db import SessionLocal
from app.models import Game, Venue, WeatherSnapshot
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


# ============================================================
# Historical weather - from CFBD directly, tied to real games.
# No OpenWeather subscription needed for this - CFBD already has
# temperature, wind, precip, snowfall, humidity, pressure, and
# condition for played games.
# ============================================================

def sync_historical_weather_for_year(year: int, tracker: ApiUsageTracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    valid_game_ids = {g.id for g in db.query(Game.id).all()}
    inserted = 0
    updated = 0
    skipped_no_game = 0
    skipped_no_data = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            games_api = cfbd.GamesApi(api_client)
            results = games_api.get_weather(year=year)
            tracker.tick()

            for w in results:
                game_id = getattr(w, "id", None)
                if game_id is None or game_id not in valid_game_ids:
                    skipped_no_game += 1
                    continue

                temp = getattr(w, "temperature", None)
                if temp is None:
                    skipped_no_data += 1
                    continue

                fields = dict(
                    temp_f=temp,
                    wind_mph=getattr(w, "wind_speed", None),
                    precip_prob=getattr(w, "precipitation", None),
                    condition=getattr(w, "weather_condition", None),
                )

                existing = db.query(WeatherSnapshot).filter(
                    WeatherSnapshot.game_id == game_id
                ).first()

                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    db.add(WeatherSnapshot(game_id=game_id, **fields))
                    inserted += 1

            db.commit()
            print(f"  Year {year}: inserted {inserted}, updated {updated} "
                  f"(skipped {skipped_no_game} no matching game, {skipped_no_data} no weather data)")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_historical_weather(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_historical_weather")
    print(f"Backfilling historical weather from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_historical_weather_for_year(year, tracker)
    tracker.report()


# ============================================================
# Live/upcoming weather - OpenWeather forecast, ~5 days out max.
# Still needed - CFBD can't forecast games that haven't been played.
# ============================================================

def _fetch_forecast(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "imperial"}
    resp = httpx.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _closest_forecast_entry(forecast_list, target_time: datetime):
    best = None
    best_diff = None
    for entry in forecast_list:
        entry_time = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)
        diff = abs((entry_time - target_time).total_seconds())
        if best_diff is None or diff < best_diff:
            best = entry
            best_diff = diff
    return best


def sync_weather_for_upcoming_games(days_ahead: int = 5):
    db = SessionLocal()

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=days_ahead)

    upcoming_games = db.query(Game).filter(
        Game.start_date.isnot(None),
        Game.start_date >= now,
        Game.start_date <= window_end,
        Game.completed == False,
    ).all()

    inserted = 0
    skipped_dome = 0
    skipped_no_venue = 0
    failed = 0

    for game in upcoming_games:
        venue = db.query(Venue).filter(Venue.id == game.venue_id).first()

        if venue is None or venue.latitude is None or venue.longitude is None:
            skipped_no_venue += 1
            continue

        if venue.is_dome:
            skipped_dome += 1
            continue

        try:
            forecast = _fetch_forecast(venue.latitude, venue.longitude)
            entry = _closest_forecast_entry(forecast.get("list", []), game.start_date.replace(tzinfo=timezone.utc))

            if entry is None:
                failed += 1
                continue

            existing = db.query(WeatherSnapshot).filter(WeatherSnapshot.game_id == game.id).first()
            fields = dict(
                temp_f=entry["main"]["temp"],
                wind_mph=entry["wind"]["speed"],
                precip_prob=entry.get("pop", 0.0) * 100,
                condition=entry["weather"][0]["main"] if entry.get("weather") else None,
            )
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
            else:
                db.add(WeatherSnapshot(game_id=game.id, **fields))
            inserted += 1
            time.sleep(0.1)

        except Exception as e:
            print(f"  Failed for game {game.id} at {venue.name}: {e}")
            failed += 1

    db.commit()
    db.close()

    print(
        f"Weather forecast sync complete: inserted/updated {inserted} snapshots "
        f"(skipped {skipped_dome} dome games, {skipped_no_venue} missing venue data, {failed} failed)"
    )


if __name__ == "__main__":
    backfill_historical_weather()