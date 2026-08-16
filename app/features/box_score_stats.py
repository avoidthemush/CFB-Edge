"""
Turnover margin and third-down conversion rate - confirmed by industry
research as core Spread/Total handicapping factors. Different data
shape than advanced stats: these live in team_season_stats/
team_stats_weekly as EAV rows (category/stat_value), not nested JSON.
Same prior-season + current-season-point-in-time pattern as everything
else - blending happens in build_team_features.py, this module only
extracts raw values.
"""
from app.models import TeamSeasonStat, TeamStatWeekly

TURNOVER_CATEGORIES = ["turnovers", "turnoversOpponent"]
THIRD_DOWN_CATEGORIES = ["thirdDownConversions", "thirdDowns",
                          "thirdDownConversionsOpponent", "thirdDownsOpponent"]
ALL_CATEGORIES = TURNOVER_CATEGORIES + THIRD_DOWN_CATEGORIES


def _compute_derived(values):
    turnovers = values.get("turnovers")
    turnovers_forced = values.get("turnoversOpponent")
    turnover_margin = (
        turnovers_forced - turnovers if turnovers is not None and turnovers_forced is not None else None
    )

    third_conv = values.get("thirdDownConversions")
    third_att = values.get("thirdDowns")
    off_third_down_pct = (third_conv / third_att) if third_conv is not None and third_att else None

    third_conv_opp = values.get("thirdDownConversionsOpponent")
    third_att_opp = values.get("thirdDownsOpponent")
    def_third_down_pct_allowed = (
        third_conv_opp / third_att_opp if third_conv_opp is not None and third_att_opp else None
    )

    return {
        "turnover_margin": turnover_margin,
        "off_third_down_pct": off_third_down_pct,
        "def_third_down_pct_allowed": def_third_down_pct_allowed,
    }


def get_prior_season_box_score_features(team_id, prior_year, db=None, cache=None):
    if cache and hasattr(cache, "season_stats_by_team_year"):
        values = cache.season_stats_by_team_year.get((team_id, prior_year), {})
    else:
        rows = db.query(TeamSeasonStat).filter(
            TeamSeasonStat.team_id == team_id, TeamSeasonStat.year == prior_year,
            TeamSeasonStat.category.in_(ALL_CATEGORIES),
        ).all()
        values = {r.category: r.stat_value for r in rows}
    return _compute_derived(values)


def get_current_season_box_score_features(team_id, year, through_week, db=None, cache=None):
    if through_week <= 0:
        return {"turnover_margin": None, "off_third_down_pct": None, "def_third_down_pct_allowed": None}

    if cache and hasattr(cache, "weekly_stats_by_team_year_week"):
        values = cache.weekly_stats_by_team_year_week.get((team_id, year, through_week), {})
    else:
        rows = db.query(TeamStatWeekly).filter(
            TeamStatWeekly.team_id == team_id, TeamStatWeekly.year == year,
            TeamStatWeekly.through_week == through_week, TeamStatWeekly.category.in_(ALL_CATEGORIES),
        ).all()
        values = {r.category: r.stat_value for r in rows}
    return _compute_derived(values)