"""
Shared coach career-quality lookup - extracted to its own module so both
build_team_features.py and coach_upgrade.py can use it without a
circular import between them.
"""


def get_coach_quality(coach_id, before_year, db=None, cache=None):
    """
    Career quality/experience for a coach, using ONLY seasons strictly
    before before_year (leakage-safe). Returns
    (career_win_pct, career_avg_sp_overall, seasons_of_experience).
    """
    if coach_id is None:
        return None, None, 0

    if cache:
        seasons = cache.coach_seasons_by_coach.get(coach_id, [])
        prior_seasons = [s for s in seasons if s.year < before_year]
    else:
        from app.models import CoachSeason
        rows = db.query(CoachSeason).filter(CoachSeason.coach_id == coach_id).all()
        prior_seasons = [s for s in rows if s.year < before_year]

    if not prior_seasons:
        return None, None, 0

    total_wins = sum(s.wins or 0 for s in prior_seasons)
    total_losses = sum(s.losses or 0 for s in prior_seasons)
    total_games = total_wins + total_losses
    win_pct = total_wins / total_games if total_games > 0 else None

    sp_values = [s.sp_overall for s in prior_seasons if s.sp_overall is not None]
    avg_sp = sum(sp_values) / len(sp_values) if sp_values else None

    return win_pct, avg_sp, len(prior_seasons)