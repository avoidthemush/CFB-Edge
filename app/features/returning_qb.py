"""
Identifies each team's returning starting QB (by prior-year passing
attempts) and whether that same player has a stats row for this team
this year - proof of roster membership for that specific year, not
just "most recently known team" (players.team_id only tracks that and
would be historically wrong for backtesting - see DESIGN_DECISIONS.md).
"""
from app.models import PlayerSeasonStat


def get_prior_year_qb1(team_id, prior_year, db=None, cache=None):
    """Returns (player_id, passing_yards, passing_attempts, passing_tds) for the team's leading passer, or None."""
    if cache and hasattr(cache, "qb1_by_team_year"):
        return cache.qb1_by_team_year.get((team_id, prior_year))

    qb1 = db.query(PlayerSeasonStat).filter(
        PlayerSeasonStat.team_id == team_id,
        PlayerSeasonStat.year == prior_year,
        PlayerSeasonStat.position == "QB",
        PlayerSeasonStat.passing_attempts.isnot(None),
    ).order_by(PlayerSeasonStat.passing_attempts.desc()).first()

    if qb1 is None:
        return None
    return (qb1.player_id, qb1.passing_yards, qb1.passing_attempts, qb1.passing_tds)


def is_qb_still_on_team(player_id, team_id, year, db=None, cache=None):
    """
    Checks if this player has a player_season_stats row for THIS team in
    THIS year - proving roster membership for that specific year.
    """
    if player_id is None:
        return False

    if cache and hasattr(cache, "player_team_years"):
        return (player_id, team_id, year) in cache.player_team_years

    match = db.query(PlayerSeasonStat).filter(
        PlayerSeasonStat.player_id == player_id,
        PlayerSeasonStat.team_id == team_id,
        PlayerSeasonStat.year == year,
    ).first()
    return match is not None


def get_returning_qb_features(team_id, year, db=None, cache=None):
    """
    Leakage-safe: uses ONLY prior_year's QB1 identity and prior_year's
    performance. "Still on team this year" reflects roster reality,
    legitimately knowable before the season - not an in-season result.
    """
    prior_year = year - 1
    qb1_info = get_prior_year_qb1(team_id, prior_year, db=db, cache=cache)

    if qb1_info is None:
        return {"returning_qb1": 0, "returning_qb1_ypa": None, "returning_qb1_prior_attempts": None}

    player_id, pass_yards, pass_attempts, pass_tds = qb1_info
    still_here = is_qb_still_on_team(player_id, team_id, year, db=db, cache=cache)

    ypa = (pass_yards / pass_attempts) if (pass_yards is not None and pass_attempts) else None

    return {
        "returning_qb1": 1 if still_here else 0,
        "returning_qb1_ypa": ypa if still_here else None,
        "returning_qb1_prior_attempts": pass_attempts if still_here else None,
    }