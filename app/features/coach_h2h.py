"""
Coach-vs-coach head-to-head history. A real, historically grounded angle
distinct from generic team strength - "does this coach have this
opponent's number." Computed entirely from games + coach_seasons, which
we already have - no new data collection needed.

Uses the same primary-coach tie-break rule as build_team_features.py
(most games coached = primary coach for a team-year), for consistency
with coaching-change detection elsewhere in the project.
"""
from collections import defaultdict
from app.models import Game, CoachSeason


def _pick_primary_coach_season(rows):
    return max(rows, key=lambda s: (s.wins or 0) + (s.losses or 0), default=None)


def build_team_coach_map(db, coach_seasons_cache=None):
    """Returns {(team_id, year): coach_id} for every team-year with a coach on record."""
    if coach_seasons_cache is not None:
        return {key: cs.coach_id for key, cs in coach_seasons_cache.items()}

    all_seasons = db.query(CoachSeason).all()
    grouped = defaultdict(list)
    for cs in all_seasons:
        grouped[(cs.team_id, cs.year)].append(cs)

    return {
        key: _pick_primary_coach_season(rows).coach_id
        for key, rows in grouped.items()
        if _pick_primary_coach_season(rows) is not None
    }


def build_h2h_index(db, team_coach_map):
    """
    {frozenset({coach_a, coach_b}): [(season, week, winning_coach_id), ...]}
    One pass over all completed games - O(1) lookup per game afterward.
    """
    games = db.query(Game).filter(Game.completed == True).all()
    index = defaultdict(list)

    for g in games:
        if g.home_points is None or g.away_points is None:
            continue
        home_coach = team_coach_map.get((g.home_team_id, g.season))
        away_coach = team_coach_map.get((g.away_team_id, g.season))
        if home_coach is None or away_coach is None or home_coach == away_coach:
            continue

        if g.home_points > g.away_points:
            winning_coach = home_coach
        elif g.away_points > g.home_points:
            winning_coach = away_coach
        else:
            winning_coach = None

        key = frozenset({home_coach, away_coach})
        index[key].append((g.season, g.week, winning_coach))

    return index


def get_h2h_record(home_coach_id, away_coach_id, before_season, before_week, h2h_index):
    """
    (home_coach_wins, home_coach_losses, meetings) for all prior meetings
    between these two specific coaches (any team), strictly before this
    game - leakage-safe, same principle as every other point-in-time
    feature in this project.
    """
    if home_coach_id is None or away_coach_id is None or home_coach_id == away_coach_id:
        return 0, 0, 0

    key = frozenset({home_coach_id, away_coach_id})
    meetings = h2h_index.get(key, [])

    wins = losses = 0
    for season, week, winning_coach in meetings:
        if season > before_season or (season == before_season and week >= before_week):
            continue
        if winning_coach == home_coach_id:
            wins += 1
        elif winning_coach == away_coach_id:
            losses += 1

    return wins, losses, wins + losses