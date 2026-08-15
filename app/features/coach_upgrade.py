"""
Refines the binary is_new_coach_year flag into a directional signal:
does the incoming coach's career quality compare favorably or
unfavorably to the departing coach's. Directly addresses the point that
a new, better coach shouldn't be penalized just for being new.
"""
from app.features.coach_quality import get_coach_quality


def get_coach_upgrade_score(team_id, year, incoming_coach_id, is_new_coach_year, db=None, cache=None):
    """
    Returns (upgrade_score, incoming_quality, departing_quality).
    upgrade_score = incoming coach's career avg SP+ minus departing
    coach's career avg SP+, using ONLY seasons strictly before `year`
    for both (leakage-safe, same principle as coach_tendencies).
    Returns (0.0, None, None) for continuity years - nothing changed,
    no upgrade/downgrade to measure.
    """
    if not is_new_coach_year or incoming_coach_id is None:
        return 0.0, None, None

    if cache:
        prior_seasons_at_team = [
            s for s in [cache.coach_seasons.get((team_id, y)) for y in range(year - 5, year)]
            if s is not None
        ]
    else:
        from app.models import CoachSeason
        prior_seasons_at_team = db.query(CoachSeason).filter(
            CoachSeason.team_id == team_id, CoachSeason.year < year, CoachSeason.year >= year - 5,
        ).order_by(CoachSeason.year.desc()).all()

    departing_coach_id = prior_seasons_at_team[0].coach_id if prior_seasons_at_team else None

    incoming_win_pct, incoming_avg_sp, _ = get_coach_quality(incoming_coach_id, year, db=db, cache=cache)
    departing_win_pct, departing_avg_sp, _ = get_coach_quality(departing_coach_id, year, db=db, cache=cache)

    if incoming_avg_sp is None or departing_avg_sp is None:
        return None, incoming_avg_sp, departing_avg_sp

    return incoming_avg_sp - departing_avg_sp, incoming_avg_sp, departing_avg_sp