"""
Bulk-preloads everything build_team_features/build_game_features need
for a year range, in a handful of queries instead of tens of thousands.
Passed in as an optional cache - when absent, those functions fall back
to their original per-call database queries (used for live single-game
prediction, where preloading a whole year range makes no sense).

Coach tie-breaking: when multiple CoachSeason rows exist for the same
team-year (mid-season interim coaching change), the row with the most
games coached (wins+losses) is treated as the primary coach - same rule
as the uncached path in build_team_features.py.
"""
from collections import defaultdict
from app.db import SessionLocal
from app.models import (
    RatingSnapshot, TeamAdvancedStat, TeamAdvancedStatWeekly, CoachSeason,
    CoachTendency, TeamTalent, RecruitingClass, OffensiveReturningProduction,
    DefensiveReturningProduction, Venue, WeatherSnapshot, CFBDBettingLine,
)
from app.features.coach_h2h import build_team_coach_map, build_h2h_index


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

        # coach_seasons: primary coach per (team_id, year) - tie-broken by
        # most games coached, same rule used everywhere else
        coach_season_candidates = defaultdict(list)
        all_coach_seasons = db.query(CoachSeason).all()  # full history needed for career quality lookups
        for r in all_coach_seasons:
            coach_season_candidates[(r.team_id, r.year)].append(r)

        self.coach_seasons = {
            key: max(rows, key=lambda s: (s.wins or 0) + (s.losses or 0))
            for key, rows in coach_season_candidates.items()
        }

        # Full career history per coach (ALL rows for that coach_id,
        # regardless of team) - needed for career quality/experience,
        # distinct from "primary coach of a team-year" above
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
        self.weather = {w.game_id: w for w in db.query(WeatherSnapshot).all()}

        self.lines_by_game = defaultdict(list)
        for line in db.query(CFBDBettingLine).all():
            self.lines_by_game[line.game_id].append(line)

        # Coach head-to-head index - built once from full coach/game
        # history, O(1) lookup per game afterward
        team_coach_map = build_team_coach_map(db, coach_seasons_cache=self.coach_seasons)
        self.team_coach_map = team_coach_map
        self.h2h_index = build_h2h_index(db, team_coach_map)

        db.close()
        print(
            f"Cache loaded: {len(self.ratings)} ratings, {len(self.adv_stats)} adv_stats, "
            f"{len(self.adv_stats_weekly)} adv_stats_weekly, {len(self.coach_seasons)} coach_seasons, "
            f"{len(self.lines_by_game)} games with lines, {len(self.h2h_index)} coach pairs with h2h history"
        )