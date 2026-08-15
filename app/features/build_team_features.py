"""
Core shared feature builder - used identically by training-data
generation and live prediction, per V2_MODEL_PLAN.md Section 4.

Aug 2026 additions: defense-side splits for offense-vs-defense matchups,
coach career quality/upgrade-score/H2H, returning QB, pace (plays per
drive), and recent-form (last game's margin, days of rest since).
"""
from app.db import SessionLocal
from app.models import (
    Team, CoachSeason, RatingSnapshot, TeamAdvancedStat, TeamAdvancedStatWeekly,
    TeamTalent, RecruitingClass, OffensiveReturningProduction,
    DefensiveReturningProduction, CoachTendency,
)
from app.features.coach_quality import get_coach_quality
from app.features.returning_qb import get_returning_qb_features
from app.features.coach_upgrade import get_coach_upgrade_score
from app.features.recent_form import get_recent_form_features

CURRENT_SEASON_RAMP_GAMES = 8
COACH_CONFIDENCE_DIVISOR = 4
COACH_CONFIDENCE_CAP = 0.6

STYLE_FIELDS = [
    "pass_rate", "off_success_rate", "off_success_rate_pass", "off_success_rate_rush",
    "off_explosiveness", "off_explosiveness_pass", "off_explosiveness_rush",
    "def_havoc_rate", "def_points_per_opportunity",
    "def_success_rate_allowed", "def_success_rate_pass_allowed", "def_success_rate_rush_allowed",
    "def_explosiveness_allowed", "def_explosiveness_pass_allowed", "def_explosiveness_rush_allowed",
    "off_line_yards", "off_power_success", "def_stuff_rate",
    "def_line_yards_allowed", "def_power_success_allowed",
    "off_plays_per_drive", "def_plays_per_drive",
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

    off_plays = _get(raw_json, "offense", "plays")
    off_drives = _get(raw_json, "offense", "drives")
    def_plays = _get(raw_json, "defense", "plays")
    def_drives = _get(raw_json, "defense", "drives")

    return {
        "pass_rate": _get(raw_json, "offense", "passingPlays", "rate"),
        "off_success_rate": _get(raw_json, "offense", "successRate"),
        "off_success_rate_pass": _get(raw_json, "offense", "passingPlays", "successRate"),
        "off_success_rate_rush": _get(raw_json, "offense", "rushingPlays", "successRate"),
        "off_explosiveness": _get(raw_json, "offense", "explosiveness"),
        "off_explosiveness_pass": _get(raw_json, "offense", "passingPlays", "explosiveness"),
        "off_explosiveness_rush": _get(raw_json, "offense", "rushingPlays", "explosiveness"),
        "def_havoc_rate": _get(raw_json, "defense", "havoc", "total"),
        "def_points_per_opportunity": _get(raw_json, "defense", "pointsPerOpportunity"),
        "def_success_rate_allowed": _get(raw_json, "defense", "successRate"),
        "def_success_rate_pass_allowed": _get(raw_json, "defense", "passingPlays", "successRate"),
        "def_success_rate_rush_allowed": _get(raw_json, "defense", "rushingPlays", "successRate"),
        "def_explosiveness_allowed": _get(raw_json, "defense", "explosiveness"),
        "def_explosiveness_pass_allowed": _get(raw_json, "defense", "passingPlays", "explosiveness"),
        "def_explosiveness_rush_allowed": _get(raw_json, "defense", "rushingPlays", "explosiveness"),
        "off_line_yards": _get(raw_json, "offense", "lineYards"),
        "off_power_success": _get(raw_json, "offense", "powerSuccess"),
        "def_stuff_rate": _get(raw_json, "defense", "stuffRate"),
        "def_line_yards_allowed": _get(raw_json, "defense", "lineYards"),
        "def_power_success_allowed": _get(raw_json, "defense", "powerSuccess"),
        "off_plays_per_drive": (off_plays / off_drives) if off_plays and off_drives else None,
        "def_plays_per_drive": (def_plays / def_drives) if def_plays and def_drives else None,
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


def _pick_primary_coach_season(rows):
    return max(rows, key=lambda s: (s.wins or 0) + (s.losses or 0), default=None)


def build_team_features(team_id: int, year: int, week: int, db=None, cache=None, game_date=None):
    """
    game_date (optional): the actual date of the game being predicted -
    needed only for recent-form features (last game margin, days of
    rest). If not provided, those two features return None rather than
    erroring - keeps this function backward-compatible for any caller
    that doesn't have a date handy.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    prior_year = year - 1
    games_played_this_season = max(week - 1, 0)
    weight_current = min(games_played_this_season / CURRENT_SEASON_RAMP_GAMES, 1.0)

    features = {}

    for system in ["sp+", "srs", "fpi"]:
        if cache:
            rating = cache.ratings.get((team_id, prior_year, system, None))
        else:
            prior = db.query(RatingSnapshot).filter(
                RatingSnapshot.team_id == team_id, RatingSnapshot.year == prior_year,
                RatingSnapshot.system == system, RatingSnapshot.week.is_(None),
            ).first()
            rating = prior.rating if prior else None
        features[f"{system}_rating"] = rating

    if cache:
        prior_elo_val = cache.ratings.get((team_id, prior_year, "elo", None))
    else:
        prior_elo = db.query(RatingSnapshot).filter(
            RatingSnapshot.team_id == team_id, RatingSnapshot.year == prior_year,
            RatingSnapshot.system == "elo", RatingSnapshot.week.is_(None),
        ).first()
        prior_elo_val = prior_elo.rating if prior_elo else None

    current_elo = None
    if games_played_this_season > 0:
        if cache:
            current_elo = cache.ratings.get((team_id, year, "elo", games_played_this_season))
        else:
            current_elo_row = db.query(RatingSnapshot).filter(
                RatingSnapshot.team_id == team_id, RatingSnapshot.year == year,
                RatingSnapshot.system == "elo", RatingSnapshot.week == games_played_this_season,
            ).first()
            current_elo = current_elo_row.rating if current_elo_row else None

    features["elo_rating"] = _blend(prior_elo_val, current_elo, weight_current)

    if cache:
        prior_adv_raw = cache.adv_stats.get((team_id, prior_year))
    else:
        prior_adv = db.query(TeamAdvancedStat).filter(
            TeamAdvancedStat.team_id == team_id, TeamAdvancedStat.year == prior_year,
        ).first()
        prior_adv_raw = prior_adv.raw_json if prior_adv else None
    prior_adv_fields = _extract_advanced_stat_fields(prior_adv_raw)

    current_adv_fields = {}
    if games_played_this_season > 0:
        if cache:
            current_adv_raw = cache.adv_stats_weekly.get((team_id, year, games_played_this_season))
        else:
            current_adv = db.query(TeamAdvancedStatWeekly).filter(
                TeamAdvancedStatWeekly.team_id == team_id, TeamAdvancedStatWeekly.year == year,
                TeamAdvancedStatWeekly.through_week == games_played_this_season,
            ).first()
            current_adv_raw = current_adv.raw_json if current_adv else None
        current_adv_fields = _extract_advanced_stat_fields(current_adv_raw)

    if cache:
        coach_season = cache.coach_seasons.get((team_id, year))
        prior_coach_season = cache.coach_seasons.get((team_id, prior_year))
    else:
        coach_season_rows = db.query(CoachSeason).filter(
            CoachSeason.team_id == team_id, CoachSeason.year == year,
        ).all()
        coach_season = _pick_primary_coach_season(coach_season_rows)

        prior_coach_season_rows = db.query(CoachSeason).filter(
            CoachSeason.team_id == team_id, CoachSeason.year == prior_year,
        ).all()
        prior_coach_season = _pick_primary_coach_season(prior_coach_season_rows)

    is_new_coach_year = (
        coach_season is not None and
        (prior_coach_season is None or prior_coach_season.coach_id != coach_season.coach_id)
    )

    coach_id = coach_season.coach_id if coach_season is not None else None

    coach_tendency = None
    if is_new_coach_year and coach_season is not None:
        if cache:
            coach_tendency = cache.coach_tendencies.get((coach_season.coach_id, year))
        else:
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

    if cache:
        talent_score = cache.talent.get((team_id, prior_year))
    else:
        talent = db.query(TeamTalent).filter(
            TeamTalent.team_id == team_id, TeamTalent.year == prior_year,
        ).first()
        talent_score = talent.talent_score if talent else None
    features["talent_score"] = talent_score

    if cache:
        recruiting = cache.recruiting.get((team_id, year))
    else:
        recruiting = db.query(RecruitingClass).filter(
            RecruitingClass.team_id == team_id, RecruitingClass.year == year,
        ).first()
    features["recruiting_rank"] = recruiting.rank if recruiting else None
    features["recruiting_points"] = recruiting.points if recruiting else None

    if cache:
        features["off_returning_ppa_pct"] = cache.off_rp.get((team_id, year))
    else:
        off_rp = db.query(OffensiveReturningProduction).filter(
            OffensiveReturningProduction.team_id == team_id, OffensiveReturningProduction.year == year,
        ).first()
        features["off_returning_ppa_pct"] = off_rp.percent_ppa if off_rp else None

    if cache:
        features["def_returning_havoc_pct"] = cache.def_rp.get((team_id, year))
    else:
        def_rp = db.query(DefensiveReturningProduction).filter(
            DefensiveReturningProduction.team_id == team_id, DefensiveReturningProduction.year == year,
        ).first()
        features["def_returning_havoc_pct"] = def_rp.percent_havoc_returning if def_rp else None

    if features["off_returning_ppa_pct"] is not None and features["recruiting_points"] is not None:
        off_new_weight = 1 - features["off_returning_ppa_pct"]
        features["off_new_talent_impact"] = off_new_weight * features["recruiting_points"]
    else:
        features["off_new_talent_impact"] = None

    if features["def_returning_havoc_pct"] is not None and features["recruiting_points"] is not None:
        def_new_weight = 1 - features["def_returning_havoc_pct"]
        features["def_new_talent_impact"] = def_new_weight * features["recruiting_points"]
    else:
        features["def_new_talent_impact"] = None

    career_win_pct, career_avg_sp, experience_seasons = get_coach_quality(
        coach_id, year, db=db, cache=cache
    )
    features["coach_id"] = coach_id
    features["coach_career_win_pct"] = career_win_pct
    features["coach_career_avg_sp"] = career_avg_sp
    features["coach_experience_seasons"] = experience_seasons

    qb_features = get_returning_qb_features(team_id, year, db=db, cache=cache)
    features.update(qb_features)

    upgrade_score, incoming_quality, departing_quality = get_coach_upgrade_score(
        team_id, year, coach_id, is_new_coach_year, db=db, cache=cache
    )
    features["coach_upgrade_score"] = upgrade_score

    form_features = get_recent_form_features(team_id, game_date, db=db, cache=cache)
    features.update(form_features)

    features["is_new_coach_year"] = is_new_coach_year
    features["games_played_this_season"] = games_played_this_season

    if own_session:
        db.close()

    return features