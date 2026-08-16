"""
Bulk-preloads everything build_team_features/build_game_features need
for a year range. Optional - functions fall back to per-call database
queries when cache is None (the live single-game prediction path).
"""
from collections import defaultdict
from app.db import SessionLocal
from app.models import (
    RatingSnapshot, TeamAdvancedStat, TeamAdvancedStatWeekly, CoachSeason,
    CoachTendency, TeamTalent, RecruitingClass, OffensiveReturningProduction,
    DefensiveReturningProduction, Venue, WeatherSnapshot, CFBDBettingLine,
    PlayerSeasonStat, TeamSeasonStat, TeamStatWeekly,
)
from app.features.coach_h2h import build_team_coach_map, build_h2h_index
from app.features.recent_form import get_prior_games_index
from app.features.rankings import get_rankings_index
from app.features.box_score_stats import ALL_CATEGORIES as BOX_SCORE_CATEGORIES


class FeatureCache:
    def __init__(self, start_year: int, end_year: int):
        db = SessionLocal()

        self.ratings = {}
        for r in db.query(RatingSnapshot).filter(
            RatingSnapshot.year >= start_year - 1, RatingSnapshot.year <= end_year
        ).all():
            self.ratings[(r.team_id, r.year, r.system, r.week)] = r.rating

        self.adv_stats = {
            (r.team_id, r.year): r.raw_json
            for r in db.query(TeamAdvancedStat).filter(
                TeamAdvancedStat.year >= start_year - 1, TeamAdvancedStat.year <= end_year
            ).all()
        }

        self.adv_stats_weekly = {
            (r.team_id, r.year, r.through_week): r.raw_json
            for r in db.query(TeamAdvancedStatWeekly).filter(
                TeamAdvancedStatWeekly.year >= start_year, TeamAdvancedStatWeekly.year <= end_year
            ).all()
        }

        coach_season_candidates = defaultdict(list)
        all_coach_seasons = db.query(CoachSeason).all()
        for r in all_coach_seasons:
            coach_season_candidates[(r.team_id, r.year)].append(r)

        self.coach_seasons = {
            key: max(rows, key=lambda s: (s.wins or 0) + (s.losses or 0))
            for key, rows in coach_season_candidates.items()
        }

        self.coach_seasons_by_coach = defaultdict(list)
        for r in all_coach_seasons:
            self.coach_seasons_by_coach[r.coach_id].append(r)
        for coach_id in self.coach_seasons_by_coach:
            self.coach_seasons_by_coach[coach_id].sort(key=lambda s: s.year)

        self.coach_tendencies = {
            (r.coach_id, r.as_of_year): r
            for r in db.query(CoachTendency).filter(
                CoachTendency.as_of_year >= start_year, CoachTendency.as_of_year <= end_year
            ).all()
        }

        self.talent = {
            (r.team_id, r.year): r.talent_score
            for r in db.query(TeamTalent).filter(
                TeamTalent.year >= start_year - 1, TeamTalent.year <= end_year
            ).all()
        }

        self.recruiting = {
            (r.team_id, r.year): r
            for r in db.query(RecruitingClass).filter(
                RecruitingClass.year >= start_year, RecruitingClass.year <= end_year
            ).all()
        }

        self.off_rp = {
            (r.team_id, r.year): r.percent_ppa
            for r in db.query(OffensiveReturningProduction).filter(
                OffensiveReturningProduction.year >= start_year, OffensiveReturningProduction.year <= end_year
            ).all()
        }

        self.def_rp = {
            (r.team_id, r.year): r.percent_havoc_returning
            for r in db.query(DefensiveReturningProduction).filter(
                DefensiveReturningProduction.year >= start_year, DefensiveReturningProduction.year <= end_year
            ).all()
        }

        self.venues = {v.id: v.is_dome for v in db.query(Venue).all()}
        self.venue_coords = {v.id: (v.latitude, v.longitude) for v in db.query(Venue).all()}
        self.weather = {w.game_id: w for w in db.query(WeatherSnapshot).all()}

        self.lines_by_game = defaultdict(list)
        for line in db.query(CFBDBettingLine).all():
            self.lines_by_game[line.game_id].append(line)

        team_coach_map = build_team_coach_map(db, coach_seasons_cache=self.coach_seasons)
        self.team_coach_map = team_coach_map
        self.h2h_index = build_h2h_index(db, team_coach_map)

        qb_rows = db.query(PlayerSeasonStat).filter(
            PlayerSeasonStat.position == "QB",
            PlayerSeasonStat.passing_attempts.isnot(None),
        ).all()

        qb1_candidates = defaultdict(list)
        for r in qb_rows:
            qb1_candidates[(r.team_id, r.year)].append(r)

        self.qb1_by_team_year = {}
        for key, rows in qb1_candidates.items():
            best = max(rows, key=lambda r: r.passing_attempts or 0)
            self.qb1_by_team_year[key] = (best.player_id, best.passing_yards, best.passing_attempts, best.passing_tds)

        self.player_team_years = {
            (r.player_id, r.team_id, r.year)
            for r in db.query(PlayerSeasonStat.player_id, PlayerSeasonStat.team_id, PlayerSeasonStat.year).all()
        }

        self.prior_games_index = get_prior_games_index(db)

        # Team's own home venue coords (for travel distance) - built from
        # the same info prior_games_index gathers, but keyed for lookup
        from collections import Counter
        home_venue_counts = defaultdict(Counter)
        for g in db.query(__import__("app.models", fromlist=["Game"]).Game).filter(
            __import__("app.models", fromlist=["Game"]).Game.home_team_id.isnot(None)
        ).all():
            if g.venue_id:
                home_venue_counts[g.home_team_id][g.venue_id] += 1
        self.team_home_venue_coords = {}
        for team_id, counts in home_venue_counts.items():
            most_common_venue_id = counts.most_common(1)[0][0]
            self.team_home_venue_coords[team_id] = self.venue_coords.get(most_common_venue_id, (None, None))

        self.rankings_by_team_year = get_rankings_index(db)

        self.season_stats_by_team_year = defaultdict(dict)
        for r in db.query(TeamSeasonStat).filter(
            TeamSeasonStat.year >= start_year - 1, TeamSeasonStat.year <= end_year,
            TeamSeasonStat.category.in_(BOX_SCORE_CATEGORIES),
        ).all():
            self.season_stats_by_team_year[(r.team_id, r.year)][r.category] = r.stat_value

        self.weekly_stats_by_team_year_week = defaultdict(dict)
        for r in db.query(TeamStatWeekly).filter(
            TeamStatWeekly.year >= start_year, TeamStatWeekly.year <= end_year,
            TeamStatWeekly.category.in_(BOX_SCORE_CATEGORIES),
        ).all():
            self.weekly_stats_by_team_year_week[(r.team_id, r.year, r.through_week)][r.category] = r.stat_value

        db.close()
        print(
            f"Cache loaded: {len(self.ratings)} ratings, {len(self.adv_stats)} adv_stats, "
            f"{len(self.adv_stats_weekly)} adv_stats_weekly, {len(self.coach_seasons)} coach_seasons, "
            f"{len(self.lines_by_game)} games with lines, {len(self.h2h_index)} coach pairs with h2h, "
            f"{len(self.qb1_by_team_year)} QB1 records, {len(self.rankings_by_team_year)} team-years ranked, "
            f"{len(self.season_stats_by_team_year)} team-years box score, "
            f"{len(self.weekly_stats_by_team_year_week)} team-year-weeks box score"
        )