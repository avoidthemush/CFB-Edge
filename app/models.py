from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db import Base


# ---------- Reference data ----------

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    school = Column(String, nullable=False)
    conference = Column(String)
    division = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_dome = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True)  # False = stub created by sync_games fallback


class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity = Column(Integer, nullable=True)
    is_dome = Column(Boolean, default=False)
    surface = Column(String, nullable=True)
    elevation = Column(Float, nullable=True)


class Coach(Base):
    """Reference table for individual coaches, keyed by CFBD's coach ID."""
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True)  # CFBD coach id
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hire_date = Column(DateTime, nullable=True)


class CoachSeason(Base):
    """One row per coach per year per team - mirrors the players/player_season_stats split."""
    __tablename__ = "coach_seasons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    year = Column(Integer, nullable=False)

    games = Column(Integer, nullable=True)
    wins = Column(Integer, nullable=True)
    losses = Column(Integer, nullable=True)
    ties = Column(Integer, nullable=True)
    win_percentage = Column(Float, nullable=True)
    preseason_rank = Column(Integer, nullable=True)
    postseason_rank = Column(Integer, nullable=True)
    srs = Column(Float, nullable=True)
    sp_overall = Column(Float, nullable=True)
    sp_offense = Column(Float, nullable=True)
    sp_defense = Column(Float, nullable=True)

    raw_json = Column(JSON, nullable=True)


# ---------- Games & core results ----------

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    season_type = Column(String, default="regular")
    start_date = Column(DateTime, nullable=True)

    home_team_id = Column(Integer, ForeignKey("teams.id"))
    away_team_id = Column(Integer, ForeignKey("teams.id"))

    home_team_name = Column(String)
    away_team_name = Column(String)

    home_points = Column(Integer, nullable=True)
    away_points = Column(Integer, nullable=True)

    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)
    venue = Column(String, nullable=True)
    neutral_site = Column(Boolean, default=False)
    attendance = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)

    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    venue_ref = relationship("Venue", foreign_keys=[venue_id])

    odds_snapshots = relationship("OddsSnapshot", back_populates="game")
    weather_snapshots = relationship("WeatherSnapshot", back_populates="game")
    cfbd_lines = relationship("CFBDBettingLine", back_populates="game")


# ---------- Odds ----------

class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    sportsbook = Column(String, nullable=False)

    pulled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    spread_home = Column(Float, nullable=True)
    spread_home_price = Column(Integer, nullable=True)
    spread_away_price = Column(Integer, nullable=True)

    total = Column(Float, nullable=True)
    over_price = Column(Integer, nullable=True)
    under_price = Column(Integer, nullable=True)

    moneyline_home = Column(Integer, nullable=True)
    moneyline_away = Column(Integer, nullable=True)

    is_closing_line = Column(Boolean, default=False)

    game = relationship("Game", back_populates="odds_snapshots")


class CFBDBettingLine(Base):
    __tablename__ = "cfbd_betting_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    provider = Column(String, nullable=True)

    spread = Column(Float, nullable=True)
    spread_open = Column(Float, nullable=True)
    over_under = Column(Float, nullable=True)
    over_under_open = Column(Float, nullable=True)
    home_moneyline = Column(Integer, nullable=True)
    away_moneyline = Column(Integer, nullable=True)

    synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    game = relationship("Game", back_populates="cfbd_lines")


# ---------- Weather ----------

class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)

    pulled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    temp_f = Column(Float, nullable=True)
    wind_mph = Column(Float, nullable=True)
    precip_prob = Column(Float, nullable=True)
    condition = Column(String, nullable=True)

    game = relationship("Game", back_populates="weather_snapshots")


# ---------- Team stats & advanced metrics ----------

class TeamSeasonStat(Base):
    __tablename__ = "team_season_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    season_type = Column(String, default="regular")
    category = Column(String, nullable=False)
    stat_value = Column(Float, nullable=True)


class TeamAdvancedStat(Base):
    __tablename__ = "team_advanced_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    raw_json = Column(JSON, nullable=False)


class RatingSnapshot(Base):
    __tablename__ = "rating_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    week = Column(Integer, nullable=True)
    system = Column(String, nullable=False)

    rating = Column(Float, nullable=True)
    offense_rating = Column(Float, nullable=True)
    defense_rating = Column(Float, nullable=True)
    raw_json = Column(JSON, nullable=True)


class TeamATS(Base):
    __tablename__ = "team_ats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    ats_wins = Column(Integer, nullable=True)
    ats_losses = Column(Integer, nullable=True)
    ats_pushes = Column(Integer, nullable=True)
    raw_json = Column(JSON, nullable=True)


# ---------- Talent, recruiting, roster continuity ----------

class TeamTalent(Base):
    __tablename__ = "team_talent"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    talent_score = Column(Float, nullable=True)


class RecruitingClass(Base):
    __tablename__ = "recruiting_classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=True)
    points = Column(Float, nullable=True)
    raw_json = Column(JSON, nullable=True)


class OffensiveReturningProduction(Base):
    __tablename__ = "offensive_returning_production"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)

    total_ppa = Column(Float, nullable=True)
    total_passing_ppa = Column(Float, nullable=True)
    total_receiving_ppa = Column(Float, nullable=True)
    total_rushing_ppa = Column(Float, nullable=True)
    percent_ppa = Column(Float, nullable=True)
    percent_passing_ppa = Column(Float, nullable=True)
    percent_receiving_ppa = Column(Float, nullable=True)
    percent_rushing_ppa = Column(Float, nullable=True)
    usage = Column(Float, nullable=True)
    passing_usage = Column(Float, nullable=True)
    receiving_usage = Column(Float, nullable=True)
    rushing_usage = Column(Float, nullable=True)

    raw_json = Column(JSON, nullable=True)


class TransferPortalEntry(Base):
    __tablename__ = "transfer_portal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    origin_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    destination_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    year = Column(Integer, nullable=False)
    transfer_date = Column(DateTime, nullable=True)
    rating = Column(Float, nullable=True)
    stars = Column(Integer, nullable=True)
    eligibility = Column(String, nullable=True)
    raw_json = Column(JSON, nullable=True)


# ---------- Rankings ----------

class PollRanking(Base):
    __tablename__ = "poll_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    poll = Column(String, nullable=False)
    rank = Column(Integer, nullable=True)
    points = Column(Float, nullable=True)



class TeamSourceAlias(Base):
    """
    Maps a CFBD team (source of truth) to the name/identifier used by
    another data source. team_id is nullable to allow tracking names we
    haven't resolved yet - those rows get updated once identified, rather
    than being silently dropped.
    """
    __tablename__ = "team_source_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    source = Column(String, nullable=False)
    source_name = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    verified = Column(Boolean, default=False)



class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    class_year = Column(String, nullable=True)
    height = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    home_city = Column(String, nullable=True)
    home_state = Column(String, nullable=True)
    home_country = Column(String, nullable=True)
    recruit_ids = Column(JSON, nullable=True)
    has_complete_bio = Column(Boolean, default=True)  # False = CFBD only gave us a thin record (common for smaller/HBCU programs) - see DESIGN_DECISIONS.md


class PlayerSeasonStat(Base):
    """
    One row per player per season. Captures both defensive counting stats
    (the primary goal - defensive returning production) and offensive
    counting stats (captured for free, since get_player_season_stats
    returns all categories in one call regardless).
    """
    __tablename__ = "player_season_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    year = Column(Integer, nullable=False)
    position = Column(String, nullable=True)  # season-specific, may differ from players.position

    # Defensive
    tackles_total = Column(Float, nullable=True)
    tackles_solo = Column(Float, nullable=True)
    tackles_for_loss = Column(Float, nullable=True)
    sacks = Column(Float, nullable=True)
    passes_defended = Column(Float, nullable=True)
    qb_hurries = Column(Float, nullable=True)
    interceptions = Column(Float, nullable=True)
    interception_yards = Column(Float, nullable=True)
    interception_tds = Column(Float, nullable=True)
    fumbles_recovered = Column(Float, nullable=True)
    defensive_tds = Column(Float, nullable=True)

    # Offensive (captured for free from the same API call)
    passing_completions = Column(Float, nullable=True)
    passing_attempts = Column(Float, nullable=True)
    passing_yards = Column(Float, nullable=True)
    passing_tds = Column(Float, nullable=True)
    passing_ints = Column(Float, nullable=True)
    rushing_carries = Column(Float, nullable=True)
    rushing_yards = Column(Float, nullable=True)
    rushing_tds = Column(Float, nullable=True)
    receiving_receptions = Column(Float, nullable=True)
    receiving_yards = Column(Float, nullable=True)
    receiving_tds = Column(Float, nullable=True)

    usage_overall = Column(Float, nullable=True)
    raw_json = Column(JSON, nullable=True)



# Our own defensive equivalent to returning_production (which is
# offense-only, per CFBD). Uses verified havoc-rate components (TFL,
# passes defended, fumbles recovered - NOT sacks or interceptions
# separately, since those are subsets already included in TFL and PD
# respectively - see DESIGN_DECISIONS.md).
# 'year' is the season being computed FOR - e.g. year=2026 uses 2025
# stats as the production baseline and 2026 rosters to determine who's
# still here. Computed via calc_defensive_returning_production.py, not
# pulled from any API.
class DefensiveReturningProduction(Base):
    __tablename__ = "defensive_returning_production"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)

    total_tfl_prior_year = Column(Float, nullable=True)
    total_pd_prior_year = Column(Float, nullable=True)
    total_fumbles_rec_prior_year = Column(Float, nullable=True)
    total_havoc_prior_year = Column(Float, nullable=True)

    tfl_returning = Column(Float, nullable=True)
    pd_returning = Column(Float, nullable=True)
    fumbles_rec_returning = Column(Float, nullable=True)
    havoc_returning = Column(Float, nullable=True)

    percent_tfl_returning = Column(Float, nullable=True)
    percent_pd_returning = Column(Float, nullable=True)
    percent_fumbles_rec_returning = Column(Float, nullable=True)
    percent_havoc_returning = Column(Float, nullable=True)

    players_prior_year_count = Column(Integer, nullable=True)
    players_returning_count = Column(Integer, nullable=True)



class TeamStatWeekly(Base):
    """
    Point-in-time version of team_season_stats - same EAV shape
    (category/stat_value), but scoped to games through a specific week
    (via CFBD's end_week param), not the full season. Used for live
    in-season model features, blended with prior-season baseline - see
    V2_MODEL_PLAN.md Section 4.
    """
    __tablename__ = "team_stats_weekly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    through_week = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    stat_value = Column(Float, nullable=True)


class TeamAdvancedStatWeekly(Base):
    """Point-in-time version of team_advanced_stats - same JSONB shape, scoped through a specific week."""
    __tablename__ = "team_advanced_stats_weekly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)
    through_week = Column(Integer, nullable=False)
    raw_json = Column(JSON, nullable=True)



class CoachTendency(Base):
    """
    Computed coach identity profile - pace/style and defensive tendencies,
    built from CoachSeason + TeamAdvancedStat, using ONLY seasons strictly
    before as_of_year (leakage-safe). Recency-weighted: more recent
    seasons count more. seasons_used is the confidence signal - a coach
    with 1 prior season should carry less weight in the blend than one
    with 8. Applied downstream as a fading prior on new-coach team-years
    only - see V2_MODEL_PLAN.md.
    """
    __tablename__ = "coach_tendencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    as_of_year = Column(Integer, nullable=False)
    seasons_used = Column(Integer, nullable=False)

    pass_rate = Column(Float, nullable=True)
    off_success_rate = Column(Float, nullable=True)
    off_success_rate_pass = Column(Float, nullable=True)
    off_success_rate_rush = Column(Float, nullable=True)
    off_explosiveness = Column(Float, nullable=True)
    def_havoc_rate = Column(Float, nullable=True)
    def_points_per_opportunity = Column(Float, nullable=True)

    raw_json = Column(JSON, nullable=True)

class BettingSystem(Base):
    """
    Reference table for every named betting system/tag (General Model,
    Mid-Season Dog, and future Total/Moneyline systems). Reused across
    all three bet types via bet_type, not one table per model.
    """
    __tablename__ = "betting_systems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system_name = Column(String, nullable=False)  # e.g. "Mid-Season Dog"
    bet_type = Column(String, nullable=False)  # "spread", "total", "moneyline"
    category = Column(String, nullable=False)  # "general" or "focused_value"
    description = Column(String, nullable=True)
    rule_definition = Column(JSON, nullable=True)  # e.g. {"min_week": 5, "underdog_only": true, ...}
    status = Column(String, nullable=False, default="approved")  # approved / under_bar / discarded

    # Backtested validation stats, from the walk-forward + bootstrap process
    pooled_win_rate = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    bootstrap_pct_profitable = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=True)
    years_tested = Column(String, nullable=True)  # e.g. "2022-2025"

    created_at = Column(DateTime, default=datetime.utcnow)


class ModelPrediction(Base):
    """
    One row per game per system it qualifies for. If a game qualifies
    for General Model AND Mid-Season Dog, that's two rows sharing the
    same underlying prediction. actual_outcome filled in once the game
    completes - this is what powers real live performance tracking.
    """
    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    system_id = Column(Integer, ForeignKey("betting_systems.id"), nullable=False)
    bet_type = Column(String, nullable=False)

    predicted_value = Column(Float, nullable=True)  # probability or predicted margin, depending on bet_type
    bet_on_home = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)

    market_spread_open = Column(Float, nullable=True)
    market_spread_current = Column(Float, nullable=True)

    predicted_at = Column(DateTime, default=datetime.utcnow)
    model_version = Column(String, nullable=True)  # e.g. filename/hash of the .joblib used

    # Filled in later, once the game is actually played
    actual_outcome = Column(String, nullable=True)  # "win", "loss", "push", or None if not graded yet
    graded_at = Column(DateTime, nullable=True)


class GameFeatureCache(Base):
    """
    Weekly-refreshed cache of build_game_features() output per game -
    the expensive part (FeatureCache build + team-level computation,
    ~2 min for a full slate) decoupled from the cheap part (checking a
    fresh odds line against already-known feature values, meant to run
    every 5 minutes). Read by the 5-min market-check job, written by
    the weekly refresh job.
    """
    __tablename__ = "game_feature_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, unique=True)
    features = Column(JSON, nullable=False)  # full build_game_features() output dict
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TeamRecentForm(Base):
    """
    Materialized, daily-refreshed rolling last-10-games record per team -
    ATS, Over/Under, and straight-up (SU) win/loss. One row per team,
    overwritten each day by run_daily_sync.py, NOT a historical log.

    Correctly crosses season boundaries: "last 10" always means the
    most recent 10 completed games for this team regardless of season,
    not "last 10 games this season" - critical for Week 1-2 of a new
    season, where most of a team's recent history is still last season.
    """
    __tablename__ = "team_recent_form"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, unique=True)

    games_counted = Column(Integer, nullable=False)  # usually 10, fewer if team has <10 games in our data

    ats_wins = Column(Integer, nullable=False, default=0)
    ats_losses = Column(Integer, nullable=False, default=0)
    ats_pushes = Column(Integer, nullable=False, default=0)

    ou_overs = Column(Integer, nullable=False, default=0)
    ou_unders = Column(Integer, nullable=False, default=0)
    ou_pushes = Column(Integer, nullable=False, default=0)

    su_wins = Column(Integer, nullable=False, default=0)
    su_losses = Column(Integer, nullable=False, default=0)

    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)