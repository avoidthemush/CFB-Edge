"""
Ranked opponent flag - real market factor (public perception of ranked
teams affects lines) confirmed by industry research. Uses AP Top 25 as
the canonical poll. Leakage-safe: only counts a ranking from a week
STRICTLY BEFORE the game being predicted - Week 1 games correctly show
as unranked/no-data rather than guessing at a preseason poll.
"""
CANONICAL_POLL = "AP Top 25"


def get_rankings_index(db):
    from app.models import PollRanking
    rows = db.query(PollRanking).filter(PollRanking.poll == CANONICAL_POLL).all()
    index = {}
    for r in rows:
        index.setdefault((r.team_id, r.year), []).append((r.week, r.rank))
    for key in index:
        index[key].sort()
    return index


def get_prior_rank(team_id, year, week, db=None, cache=None):
    if cache and hasattr(cache, "rankings_by_team_year"):
        team_rankings = cache.rankings_by_team_year.get((team_id, year), [])
    else:
        index = get_rankings_index(db)
        team_rankings = index.get((team_id, year), [])

    prior = [r for r in team_rankings if r[0] < week]
    if not prior:
        return {"is_ranked": 0, "rank": None}

    _, most_recent_rank = prior[-1]
    return {"is_ranked": 1, "rank": most_recent_rank}