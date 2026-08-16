"""
Away-team travel distance for a game (haversine distance between the
away team's home venue and this game's venue), and the same calculation
for that team's PRIOR game - lets us test both "traveled far for this
game" and "traveled far last game, playing again soon after" (short-
week travel fatigue) as separate, testable hypotheses.
"""
import math


def haversine_miles(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_team_home_venue_coords(team_id, db=None, cache=None):
    """A team's own home venue (from its most common home-game venue) lat/long."""
    if cache and hasattr(cache, "team_home_venue_coords"):
        return cache.team_home_venue_coords.get(team_id, (None, None))

    from app.models import Game, Venue
    from collections import Counter

    home_games = db.query(Game.venue_id).filter(Game.home_team_id == team_id).all()
    if not home_games:
        return None, None

    most_common_venue_id = Counter(v[0] for v in home_games if v[0] is not None).most_common(1)
    if not most_common_venue_id:
        return None, None

    venue = db.query(Venue).filter(Venue.id == most_common_venue_id[0][0]).first()
    if venue is None:
        return None, None
    return venue.latitude, venue.longitude


def get_travel_distance_for_game(team_id, venue_lat, venue_lon, db=None, cache=None):
    """Distance from team_id's own home venue to this game's venue (0 if playing at home)."""
    home_lat, home_lon = get_team_home_venue_coords(team_id, db=db, cache=cache)
    return haversine_miles(home_lat, home_lon, venue_lat, venue_lon)