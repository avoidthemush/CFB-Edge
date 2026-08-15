"""
'Recent form' features: how did this team's last game go, and how much
rest have they had since. Built from games.home_points/away_points and
games.start_date directly - a different data source than the advanced-
stats-derived features, same leakage-safe principle: only ever looks at
games STRICTLY BEFORE the one being predicted.
"""


def get_prior_games_index(db):
    """
    {team_id: [(game_date, margin_for_this_team), ...]} sorted by date,
    for every completed game. Built once, reused across all lookups.
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
        index.setdefault(g.home_team_id, []).append((g.start_date, home_margin))
        index.setdefault(g.away_team_id, []).append((g.start_date, -home_margin))

    for team_id in index:
        index[team_id].sort(key=lambda x: x[0])

    return index


def get_recent_form_features(team_id, game_date, db=None, cache=None):
    """
    Returns last_game_margin/days_since_last_game using ONLY games
    strictly before game_date - leakage-safe. All None if game_date is
    None (caller didn't provide it) or no prior game exists.
    """
    if game_date is None:
        return {"last_game_margin": None, "days_since_last_game": None}

    if cache and hasattr(cache, "prior_games_index"):
        team_games = cache.prior_games_index.get(team_id, [])
    else:
        index = get_prior_games_index(db)
        team_games = index.get(team_id, [])

    prior = [g for g in team_games if g[0] < game_date]
    if not prior:
        return {"last_game_margin": None, "days_since_last_game": None}

    last_date, last_margin = prior[-1]
    days_since = (game_date - last_date).days

    return {"last_game_margin": last_margin, "days_since_last_game": days_since}