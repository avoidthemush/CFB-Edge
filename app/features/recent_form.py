"""
'Recent form' features: how did this team's last game go, how much rest
since, and (extended Aug 2026) where was that last game played - powers
both recent-form and "game after a long trip" travel-fatigue features.
Leakage-safe: only ever looks at games STRICTLY BEFORE the one being
predicted.
"""


def get_prior_games_index(db):
    """
    {team_id: [(game_date, margin_for_this_team, venue_id), ...]} sorted
    by date, for every completed game. Built once, reused everywhere.
    """
    from app.models import Game
    games = db.query(Game).filter(
        Game.completed == True,
        Game.home_points.isnot(None),
        Game.away_points.isnot(None),
    ).all()

    index = {}
    for g in games:
        home_margin = g.home_points - g.away_points
        index.setdefault(g.home_team_id, []).append((g.start_date, home_margin, g.venue_id))
        index.setdefault(g.away_team_id, []).append((g.start_date, -home_margin, g.venue_id))

    for team_id in index:
        index[team_id].sort(key=lambda x: x[0])

    return index


def get_recent_form_features(team_id, game_date, db=None, cache=None):
    if game_date is None:
        return {"last_game_margin": None, "days_since_last_game": None, "last_game_venue_id": None}

    if cache and hasattr(cache, "prior_games_index"):
        team_games = cache.prior_games_index.get(team_id, [])
    else:
        index = get_prior_games_index(db)
        team_games = index.get(team_id, [])

    prior = [g for g in team_games if g[0] < game_date]
    if not prior:
        return {"last_game_margin": None, "days_since_last_game": None, "last_game_venue_id": None}

    last_date, last_margin, last_venue_id = prior[-1]
    days_since = (game_date - last_date).days

    return {
        "last_game_margin": last_margin,
        "days_since_last_game": days_since,
        "last_game_venue_id": last_venue_id,
    }