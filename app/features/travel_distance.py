"""
Travel distance: current-game travel for each team, and (Aug 2026
addition) the PRIOR game's travel distance - captures "traveled far
last week, playing again soon" fatigue, not just "traveling far today."
"""
import math
from collections import Counter


def haversine_miles(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_team_home_venue_coords(team_id, db=None, cache=None):
    if cache and hasattr(cache, "team_home_venue_coords"):
        return cache.team_home_venue_coords.get(team_id, (None, None))

    from app.models import Game, Venue
    home_games = db.query(Game.venue_id).filter(Game.home_team_id == team_id).all()
    if not home_games:
        return None, None

    most_common = Counter(v[0] for v in home_games if v[0] is not None).most_common(1)
    if not most_common:
        return None, None

    venue = db.query(Venue).filter(Venue.id == most_common[0][0]).first()
    if venue is None:
        return None, None
    return venue.latitude, venue.longitude


def get_venue_coords(venue_id, db=None, cache=None):
    if venue_id is None:
        return None, None
    if cache and hasattr(cache, "venue_coords"):
        return cache.venue_coords.get(venue_id, (None, None))

    from app.models import Venue
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if venue is None:
        return None, None
    return venue.latitude, venue.longitude


def get_travel_distance_for_game(team_id, venue_lat, venue_lon, db=None, cache=None):
    home_lat, home_lon = get_team_home_venue_coords(team_id, db=db, cache=cache)
    return haversine_miles(home_lat, home_lon, venue_lat, venue_lon)


def get_prior_game_travel_distance(team_id, last_game_venue_id, db=None, cache=None):
    """Distance the team traveled TO their previous game - fatigue-carryover signal."""
    if last_game_venue_id is None:
        return None
    venue_lat, venue_lon = get_venue_coords(last_game_venue_id, db=db, cache=cache)
    return get_travel_distance_for_game(team_id, venue_lat, venue_lon, db=db, cache=cache)