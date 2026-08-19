"""
Weekly cron job: computes and caches build_game_features() output for
the CURRENT WEEK's upcoming FBS-vs-FBS games only - not future weeks
(their predictions would be stale by the time they're relevant, and
recomputing them repeatedly is wasted cost) and not past weeks (already
completed, no longer need live prediction).

Run this whenever weekly stats/ratings/rankings finish syncing.
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
        # Infer current week as the earliest week with any incomplete game
        next_game = db.query(Game).filter(
            Game.season == season, Game.completed == False
        ).order_by(Game.week).first()
        current_week = next_game.week if next_game else 1

    fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}
    all_games = db.query(Game).filter(
        Game.season == season, Game.completed == False, Game.week == current_week,
    ).all()
    games = [g for g in all_games if g.home_team_id in fbs_team_ids and g.away_team_id in fbs_team_ids]

    print(f"Refreshing feature cache for week {current_week}: {len(games)} FBS-vs-FBS games")

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