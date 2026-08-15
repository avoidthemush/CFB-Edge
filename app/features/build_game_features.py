"""
Combines two teams' point-in-time profiles into game-level model inputs.

Aug 2026: offense-vs-defense MATCHUP features (pass, rush, trenches,
returning-QB-vs-pass-defense), coach quality/experience/head-to-head/
upgrade-score comparisons, talent-fades-as-season-progresses, wind x
pass-rate interaction. Only legitimate team-vs-team comparisons remain
as diffs - play-level offense/defense stats never face each other
directly and are matchup-only, not diffed against each other.
"""
from app.db import SessionLocal
from app.models import Game, Venue, WeatherSnapshot
from app.features.build_team_features import build_team_features, CURRENT_SEASON_RAMP_GAMES
from app.features.get_game_line import get_best_line_for_game
from app.features.coach_h2h import get_h2h_record, build_team_coach_map, build_h2h_index

DIFF_FIELDS = [
    "sp+_rating", "srs_rating", "fpi_rating", "elo_rating",
    "talent_score", "recruiting_points",
    "off_returning_ppa_pct", "def_returning_havoc_pct",
    "off_new_talent_impact", "def_new_talent_impact",
    "coach_career_win_pct", "coach_career_avg_sp", "coach_experience_seasons",
    "coach_upgrade_score",
]

RAW_ONLY_FIELDS = [
    "off_success_rate", "off_success_rate_pass", "off_success_rate_rush",
    "off_explosiveness", "off_explosiveness_pass", "off_explosiveness_rush",
    "def_havoc_rate", "def_points_per_opportunity",
    "def_success_rate_allowed", "def_success_rate_pass_allowed", "def_success_rate_rush_allowed",
    "off_line_yards", "off_power_success", "def_stuff_rate",
    "def_line_yards_allowed", "def_power_success_allowed",
    "off_ppa", "def_ppa",
]


def _matchup_mismatch(offense_val, defense_allowed_val):
    if offense_val is None or defense_allowed_val is None:
        return None
    return offense_val - defense_allowed_val


def build_game_features(game_id: int, db=None, cache=None, game=None):
    own_session = db is None
    if own_session:
        db = SessionLocal()

    if game is None:
        game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        if own_session:
            db.close()
        return None

    home_features = build_team_features(game.home_team_id, game.season, game.week, db=db, cache=cache)
    away_features = build_team_features(game.away_team_id, game.season, game.week, db=db, cache=cache)

    features = {"game_id": game_id, "season": game.season, "week": game.week}

    for field in DIFF_FIELDS:
        home_val = home_features.get(field)
        away_val = away_features.get(field)
        features[f"home_{field}"] = home_val
        features[f"away_{field}"] = away_val
        features[f"diff_{field}"] = (
            home_val - away_val if home_val is not None and away_val is not None else None
        )

    for field in RAW_ONLY_FIELDS:
        features[f"home_{field}"] = home_features.get(field)
        features[f"away_{field}"] = away_features.get(field)

    features["home_is_new_coach_year"] = home_features.get("is_new_coach_year")
    features["away_is_new_coach_year"] = away_features.get("is_new_coach_year")

    # --- Offense-vs-defense matchups: pass, rush ---
    features["matchup_home_pass_off_vs_away_pass_def"] = _matchup_mismatch(
        home_features.get("off_success_rate_pass"), away_features.get("def_success_rate_pass_allowed")
    )
    features["matchup_home_rush_off_vs_away_rush_def"] = _matchup_mismatch(
        home_features.get("off_success_rate_rush"), away_features.get("def_success_rate_rush_allowed")
    )
    features["matchup_away_pass_off_vs_home_pass_def"] = _matchup_mismatch(
        away_features.get("off_success_rate_pass"), home_features.get("def_success_rate_pass_allowed")
    )
    features["matchup_away_rush_off_vs_home_rush_def"] = _matchup_mismatch(
        away_features.get("off_success_rate_rush"), home_features.get("def_success_rate_rush_allowed")
    )

    # --- Trenches matchups ---
    features["matchup_home_run_block_vs_away_run_stop"] = _matchup_mismatch(
        home_features.get("off_line_yards"), away_features.get("def_line_yards_allowed")
    )
    features["matchup_away_run_block_vs_home_run_stop"] = _matchup_mismatch(
        away_features.get("off_line_yards"), home_features.get("def_line_yards_allowed")
    )
    features["matchup_home_power_vs_away_stuff"] = _matchup_mismatch(
        home_features.get("off_power_success"), away_features.get("def_stuff_rate")
    )
    features["matchup_away_power_vs_home_stuff"] = _matchup_mismatch(
        away_features.get("off_power_success"), home_features.get("def_stuff_rate")
    )

    # --- Returning QB vs. opponent's pass defense ---
    features["home_returning_qb1"] = home_features.get("returning_qb1")
    features["away_returning_qb1"] = away_features.get("returning_qb1")
    features["matchup_home_returning_qb_vs_away_pass_def"] = (
        _matchup_mismatch(home_features.get("returning_qb1_ypa"), away_features.get("def_success_rate_pass_allowed"))
        if home_features.get("returning_qb1") == 1 else None
    )
    features["matchup_away_returning_qb_vs_home_pass_def"] = (
        _matchup_mismatch(away_features.get("returning_qb1_ypa"), home_features.get("def_success_rate_pass_allowed"))
        if away_features.get("returning_qb1") == 1 else None
    )

    home_edges = [features["matchup_home_pass_off_vs_away_pass_def"],
                  features["matchup_home_rush_off_vs_away_rush_def"],
                  features["matchup_home_run_block_vs_away_run_stop"],
                  features["matchup_home_power_vs_away_stuff"]]
    away_edges = [features["matchup_away_pass_off_vs_home_pass_def"],
                  features["matchup_away_rush_off_vs_home_rush_def"],
                  features["matchup_away_run_block_vs_home_run_stop"],
                  features["matchup_away_power_vs_home_stuff"]]
    if all(v is not None for v in home_edges + away_edges):
        features["net_matchup_advantage"] = sum(home_edges) - sum(away_edges)
    else:
        features["net_matchup_advantage"] = None

    # --- Coach head-to-head history ---
    home_coach_id = home_features.get("coach_id")
    away_coach_id = away_features.get("coach_id")

    if cache:
        h2h_index = cache.h2h_index
    else:
        team_coach_map = build_team_coach_map(db)
        h2h_index = build_h2h_index(db, team_coach_map)

    h2h_wins, h2h_losses, h2h_meetings = get_h2h_record(
        home_coach_id, away_coach_id, game.season, game.week, h2h_index
    )
    features["coach_h2h_meetings"] = h2h_meetings
    features["coach_h2h_home_coach_win_pct"] = (h2h_wins / h2h_meetings) if h2h_meetings > 0 else None

    # --- Talent-fades-as-season-progresses interaction ---
    games_played = home_features.get("games_played_this_season", 0)
    season_progress = min(games_played / CURRENT_SEASON_RAMP_GAMES, 1.0)
    early_season_weight = 1.0 - season_progress

    diff_talent = features.get("diff_talent_score")
    diff_recruiting = features.get("diff_recruiting_points")
    features["talent_edge_early_season"] = (
        diff_talent * early_season_weight if diff_talent is not None else None
    )
    features["recruiting_edge_early_season"] = (
        diff_recruiting * early_season_weight if diff_recruiting is not None else None
    )

    features["neutral_site"] = game.neutral_site

    if cache:
        is_dome = cache.venues.get(game.venue_id)
    else:
        venue = db.query(Venue).filter(Venue.id == game.venue_id).first()
        is_dome = venue.is_dome if venue else None
    features["is_dome"] = is_dome

    if cache:
        weather = cache.weather.get(game_id)
    else:
        weather = db.query(WeatherSnapshot).filter(WeatherSnapshot.game_id == game_id).first()
    features["temp_f"] = weather.temp_f if weather else None
    features["wind_mph"] = weather.wind_mph if weather else None
    features["precip_prob"] = weather.precip_prob if weather else None

    wind = features["wind_mph"]
    home_pass_rate = home_features.get("pass_rate")
    away_pass_rate = away_features.get("pass_rate")
    if wind is not None and home_pass_rate is not None and away_pass_rate is not None:
        avg_pass_rate = (home_pass_rate + away_pass_rate) / 2
        features["wind_x_pass_rate"] = wind * avg_pass_rate
    else:
        features["wind_x_pass_rate"] = None

    line = get_best_line_for_game(game_id, db, cache=cache)
    if line:
        features["market_spread"] = line.spread
        features["market_spread_open"] = line.spread_open
        features["market_total"] = line.over_under
        features["market_total_open"] = line.over_under_open
        features["market_home_moneyline"] = line.home_moneyline
        features["market_away_moneyline"] = line.away_moneyline
        features["market_provider"] = line.provider
    else:
        features["market_spread"] = None
        features["market_spread_open"] = None
        features["market_total"] = None
        features["market_total_open"] = None
        features["market_home_moneyline"] = None
        features["market_away_moneyline"] = None
        features["market_provider"] = None

    if game.completed and game.home_points is not None and game.away_points is not None:
        features["actual_spread"] = game.home_points - game.away_points
        features["actual_total"] = game.home_points + game.away_points
        features["home_won"] = game.home_points > game.away_points
    else:
        features["actual_spread"] = None
        features["actual_total"] = None
        features["home_won"] = None

    if own_session:
        db.close()

    return features