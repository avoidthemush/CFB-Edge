"""
Core shared feature builder - used identically by training-data
generation and live prediction, per V2_MODEL_PLAN.md Section 4. Given a
team and a specific (year, week), returns a leakage-safe, point-in-time
blended feature dict: prior-completed-season baseline blended with
in-season-so-far data, with coach tendency folded into the prior side
for new-coach years.

"week" means: features as known BEFORE that week's games are played.
week=1 means zero games played this season - fully prior-season baseline.
"""
from app.db import SessionLocal
from app.models import (
    Team, CoachSeason, RatingSnapshot, TeamAdvancedStat, TeamAdvancedStatWeekly,
    TeamTalent, RecruitingClass, OffensiveReturningProduction,
    DefensiveReturningProduction, CoachTendency,
)

CURRENT_SEASON_RAMP_GAMES = 8
COACH_CONFIDENCE_DIVISOR = 4
COACH_CONFIDENCE_CAP = 0.6

STYLE_FIELDS = [
    "pass_rate", "off_success_rate", "off_success_rate_pass", "off_success_rate_rush",
    "off_explosiveness", "def_havoc_rate", "def_points_per_opportunity",
]


def _get(d, *path):
    for key in path:
        if d is None:
            return None
        d = d.get(key)
    return d


def _extract_advanced_stat_fields(raw_json):
    if raw_json is None:
        return {}
    return {
        "pass_rate": _get(raw_json, "offense", "passingPlays", "rate"),
        "off_success_rate": _get(raw_json, "offense", "successRate"),
        "off_success_rate_pass": _get(raw_json, "offense", "passingPlays", "successRate"),
        "off_success_rate_rush": _get(raw_json, "offense", "rushingPlays", "successRate"),
        "off_explosiveness": _get(raw_json, "offense", "explosiveness"),
        "def_havoc_rate": _get(raw_json, "defense", "havoc", "total"),
        "def_points_per_opportunity": _get(raw_json, "defense", "pointsPerOpportunity"),
        "off_ppa": _get(raw_json, "offense", "ppa"),
        "def_ppa": _get(raw_json, "defense", "ppa"),
    }


def _blend(prior_val, current_val, weight_current):
    if current_val is None and prior_val is None:
        return None
    if current_val is None:
        return prior_val
    if prior_val is None:
        return current_val
    return (1 - weight_current) * prior_val + weight_current * current_val


def build_team_features(team_id: int, year: int, week: int, db=None):
    """
    Returns a flat dict of blended, point-in-time features for one team,
    as known immediately before the given week's games. Caller owns the
    db session if passed in (for batch efficiency); opens/closes its own
    otherwise.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    prior_year = year - 1
    games_played_this_season = max(week - 1, 0)
    weight_current = min(games_played_this_season / CURRENT_SEASON_RAMP_GAMES, 1.0)

    features = {}

    # --- Ratings: SP+/SRS/FPI (prior-season only, no week data exists) + Elo (true point-in-time) ---
    for system in ["sp+", "srs", "fpi"]:
        prior = db.query(RatingSnapshot).filter(
            RatingSnapshot.team_id == team_id, RatingSnapshot.year == prior_year,
            RatingSnapshot.system == system, RatingSnapshot.week.is_(None),
        ).first()
        features[f"{system}_rating"] = prior.rating if prior else None

    prior_elo = db.query(RatingSnapshot).filter(
        RatingSnapshot.team_id == team_id, RatingSnapshot.year == prior_year,
        RatingSnapshot.system == "elo", RatingSnapshot.week.is_(None),
    ).first()
    current_elo = None
    if games_played_this_season > 0:
        current_elo_row = db.query(RatingSnapshot).filter(
            RatingSnapshot.team_id == team_id, RatingSnapshot.year == year,
            RatingSnapshot.system == "elo", RatingSnapshot.week == games_played_this_season,
        ).first()
        current_elo = current_elo_row.rating if current_elo_row else None
    features["elo_rating"] = _blend(
        prior_elo.rating if prior_elo else None, current_elo, weight_current
    )

    # --- Advanced/style stats: prior-season final + current-season-through-last-week, blended ---
    prior_adv = db.query(TeamAdvancedStat).filter(
        TeamAdvancedStat.team_id == team_id, TeamAdvancedStat.year == prior_year,
    ).first()
    prior_adv_fields = _extract_advanced_stat_fields(prior_adv.raw_json if prior_adv else None)

    current_adv_fields = {}
    if games_played_this_season > 0:
        current_adv = db.query(TeamAdvancedStatWeekly).filter(
            TeamAdvancedStatWeekly.team_id == team_id, TeamAdvancedStatWeekly.year == year,
            TeamAdvancedStatWeekly.through_week == games_played_this_season,
        ).first()
        current_adv_fields = _extract_advanced_stat_fields(current_adv.raw_json if current_adv else None)

    # --- Coach tendency adjustment (only affects the PRIOR side of style fields) ---
    coach_season = db.query(CoachSeason).filter(
        CoachSeason.team_id == team_id, CoachSeason.year == year,
    ).first()
    prior_coach_season = db.query(CoachSeason).filter(
        CoachSeason.team_id == team_id, CoachSeason.year == prior_year,
    ).first()
    is_new_coach_year = (
        coach_season is not None and
        (prior_coach_season is None or prior_coach_season.coach_id != coach_season.coach_id)
    )

    coach_tendency = None
    if is_new_coach_year and coach_season is not None:
        coach_tendency = db.query(CoachTendency).filter(
            CoachTendency.coach_id == coach_season.coach_id,
            CoachTendency.as_of_year == year,
        ).first()

    for field in STYLE_FIELDS:
        prior_val = prior_adv_fields.get(field)
        if coach_tendency is not None:
            coach_val = getattr(coach_tendency, field, None)
            if coach_val is not None:
                coach_weight = min(coach_tendency.seasons_used / COACH_CONFIDENCE_DIVISOR, COACH_CONFIDENCE_CAP)
                if prior_val is not None:
                    prior_val = coach_weight * coach_val + (1 - coach_weight) * prior_val
                else:
                    prior_val = coach_val

        current_val = current_adv_fields.get(field)
        features[field] = _blend(prior_val, current_val, weight_current)

    for field in ["off_ppa", "def_ppa"]:
        features[field] = _blend(prior_adv_fields.get(field), current_adv_fields.get(field), weight_current)

    # --- Prior-season-only baselines (talent, recruiting, returning production) ---
    talent = db.query(TeamTalent).filter(
        TeamTalent.team_id == team_id, TeamTalent.year == prior_year,
    ).first()
    features["talent_score"] = talent.talent_score if talent else None

    recruiting = db.query(RecruitingClass).filter(
        RecruitingClass.team_id == team_id, RecruitingClass.year == year,
    ).first()
    features["recruiting_rank"] = recruiting.rank if recruiting else None
    features["recruiting_points"] = recruiting.points if recruiting else None

    off_rp = db.query(OffensiveReturningProduction).filter(
        OffensiveReturningProduction.team_id == team_id, OffensiveReturningProduction.year == year,
    ).first()
    features["off_returning_ppa_pct"] = off_rp.percent_ppa if off_rp else None

    def_rp = db.query(DefensiveReturningProduction).filter(
        DefensiveReturningProduction.team_id == team_id, DefensiveReturningProduction.year == year,
    ).first()
    features["def_returning_havoc_pct"] = def_rp.percent_havoc_returning if def_rp else None

    features["is_new_coach_year"] = is_new_coach_year
    features["games_played_this_season"] = games_played_this_season

    if own_session:
        db.close()

    return features