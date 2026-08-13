"""
Combines two teams' point-in-time profiles (build_team_features) into
game-level model inputs: differentials, raw paired values, weather,
market line, and context flags. Also returns the training targets
(actual outcome) when the game is completed.

Optional `cache` (FeatureCache) is passed through to sub-calls for bulk
dataset generation. Omit for live single-game prediction.
"""
from app.db import SessionLocal
from app.models import Game, Venue, WeatherSnapshot
from app.features.build_team_features import build_team_features
from app.features.get_game_line import get_best_line_for_game

DIFF_FIELDS = [
    "sp+_rating", "srs_rating", "fpi_rating", "elo_rating",
    "pass_rate", "off_success_rate", "off_success_rate_pass", "off_success_rate_rush",
    "off_explosiveness", "def_havoc_rate", "def_points_per_opportunity",
    "off_ppa", "def_ppa", "talent_score", "recruiting_points",
    "off_returning_ppa_pct", "def_returning_havoc_pct",
]


def build_game_features(game_id: int, db=None, cache=None):
    own_session = db is None
    if own_session:
        db = SessionLocal()

    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        if own_session:
            db.close()
        return None

    home_features = build_team_features(game.home_team_id, game.season, game.week, db=db, cache=cache)
    away_features = build_team_features(game.away_team_id, game.season, game.week, db=db, cache=cache)

    features = {"game_id": game_id, "season": game.season, "week": game.week}

    for field in DIFF_FIELDS:
        home_val = home_features.get(field)
        away_val = away_features.get(field)
        features[f"home_{field}"] = home_val
        features[f"away_{field}"] = away_val
        features[f"diff_{field}"] = (
            home_val - away_val if home_val is not None and away_val is not None else None
        )

    features["home_is_new_coach_year"] = home_features.get("is_new_coach_year")
    features["away_is_new_coach_year"] = away_features.get("is_new_coach_year")

    features["neutral_site"] = game.neutral_site

    if cache:
        is_dome = cache.venues.get(game.venue_id)
    else:
        venue = db.query(Venue).filter(Venue.id == game.venue_id).first()
        is_dome = venue.is_dome if venue else None
    features["is_dome"] = is_dome

    if cache:
        weather = cache.weather.get(game_id)
    else:
        weather = db.query(WeatherSnapshot).filter(WeatherSnapshot.game_id == game_id).first()
    features["temp_f"] = weather.temp_f if weather else None
    features["wind_mph"] = weather.wind_mph if weather else None
    features["precip_prob"] = weather.precip_prob if weather else None

    line = get_best_line_for_game(game_id, db, cache=cache)
    if line:
        features["market_spread"] = line.spread
        features["market_spread_open"] = line.spread_open
        features["market_total"] = line.over_under
        features["market_total_open"] = line.over_under_open
        features["market_home_moneyline"] = line.home_moneyline
        features["market_away_moneyline"] = line.away_moneyline
        features["market_provider"] = line.provider
    else:
        features["market_spread"] = None
        features["market_spread_open"] = None
        features["market_total"] = None
        features["market_total_open"] = None
        features["market_home_moneyline"] = None
        features["market_away_moneyline"] = None
        features["market_provider"] = None

    if game.completed and game.home_points is not None and game.away_points is not None:
        features["actual_spread"] = game.home_points - game.away_points
        features["actual_total"] = game.home_points + game.away_points
        features["home_won"] = game.home_points > game.away_points
    else:
        features["actual_spread"] = None
        features["actual_total"] = None
        features["home_won"] = None

    if own_session:
        db.close()

    return features