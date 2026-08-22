"""
Weekly job: computes and caches build_game_features() output for the
CURRENT WEEK's upcoming FBS-vs-FBS games only.

REAL BUG FOUND AND FIXED (Aug 22, 2026): the very first test run of
this script (before "current week only" scoping was added) inserted
ALL 761 season games into game_feature_cache. When scoping was added
later, it only changed what gets ADDED/UPDATED going forward - it never
deleted those original 761 stale rows. Every predict_week.py script
(when run without an explicit week argument, as the odds-poll cron job
does) was reading and acting on ALL of them, generating real
predictions for future weeks using team-feature snapshots frozen from
days ago. Fixed by actively deleting any cached row outside the current
week's scope, every time this runs - the cache table now always
reflects ONLY what it's supposed to.
"""
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, Team, GameFeatureCache
from app.features.build_game_features import build_game_features
from app.features.feature_cache import FeatureCache
from app.config import CURRENT_SEASON


def refresh_cache(season: int = CURRENT_SEASON, current_week: int = None):
    db = SessionLocal()

    if current_week is None:
        next_game = db.query(Game).filter(
            Game.season == season, Game.completed == False
        ).order_by(Game.week).first()
        current_week = next_game.week if next_game else 1

    fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}
    all_games = db.query(Game).filter(
        Game.season == season, Game.completed == False, Game.week == current_week,
    ).all()
    games = [g for g in all_games if g.home_team_id in fbs_team_ids and g.away_team_id in fbs_team_ids]
    in_scope_game_ids = {g.id for g in games}

    print(f"Refreshing feature cache for week {current_week}: {len(games)} FBS-vs-FBS games")

    # Prune anything outside this week's scope - real fix for stale
    # rows left over from before this scoping existed.
    stale_rows = (
        db.query(GameFeatureCache)
        .join(Game, GameFeatureCache.game_id == Game.id)
        .filter(Game.season == season, GameFeatureCache.game_id.notin_(in_scope_game_ids))
        .all()
    )
    if stale_rows:
        print(f"Pruning {len(stale_rows)} stale/out-of-scope cached games (from before current-week scoping)")
        for row in stale_rows:
            db.delete(row)
        db.commit()

    cache = FeatureCache(start_year=season, end_year=season)

    refreshed = 0
    for game in games:
        features = build_game_features(game.id, cache=cache, game=game, db=db)
        if features is None:
            continue

        existing = db.query(GameFeatureCache).filter(GameFeatureCache.game_id == game.id).first()
        if existing:
            existing.features = features
            existing.computed_at = datetime.utcnow()
        else:
            db.add(GameFeatureCache(game_id=game.id, features=features, computed_at=datetime.utcnow()))
        refreshed += 1

    db.commit()
    print(f"Refreshed {refreshed} games' feature cache.")
    db.close()


if __name__ == "__main__":
    import sys
    week_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    refresh_cache(current_week=week_arg)