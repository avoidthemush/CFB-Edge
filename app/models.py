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
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    year = Column(Integer, nullable=False)
    wins = Column(Integer, nullable=True)
    losses = Column(Integer, nullable=True)
    ties = Column(Integer, nullable=True)
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


class ReturningProduction(Base):
    __tablename__ = "returning_production"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    year = Column(Integer, nullable=False)

    # Offense-side data from CFBD (no defensive equivalent exists there -
    # see defensive_returning_production table, built separately, for our
    # own proxy metric)
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
    position = Column(String, nullable=True)
    origin_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    destination_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    year = Column(Integer, nullable=False)
    rating = Column(Float, nullable=True)
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