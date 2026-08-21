"""
Runs the approved Unranked Favorite Dog system using CACHED features
and BATCHED live odds lookups. Qualification (dog spread size, which
side is the underdog) is checked against the CURRENT line, not the
opening line - matching the same live-decision correction applied to
Spread's predict_week.py.
"""
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction, GameFeatureCache
from app.features.get_game_line import get_live_book_lines_batch
from app.config import CURRENT_SEASON

MAX_DOG_SPREAD = 10
SYSTEM_DB_NAME = "Unranked Favorite Dog"


def evaluate_game(cached_features, book_lines):
    results = []
    for book, line in book_lines.items():
        if line.spread is None or line.spread == 0:
            continue

        home_is_dog = line.spread > 0
        dog_spread_size = abs(line.spread)
        if dog_spread_size > MAX_DOG_SPREAD:
            continue

        favorite_is_ranked = cached_features.get("away_is_ranked") if home_is_dog else cached_features.get("home_is_ranked")
        if favorite_is_ranked is None or favorite_is_ranked == 1:
            continue

        dog_ml = line.home_moneyline if home_is_dog else line.away_moneyline
        if dog_ml is None:
            continue

        bet_side = "HOME" if home_is_dog else "AWAY"
        results.append((book, bet_side, dog_ml, line.spread))

    return results


def _upsert_prediction(db, game_id, system_id, book, dog_ml, spread_current, bet_side):
    version_tag = f"unranked_favorite_dog_rule:{book}"
    existing = db.query(ModelPrediction).filter(
        ModelPrediction.game_id == game_id, ModelPrediction.system_id == system_id,
        ModelPrediction.model_version == version_tag,
    ).first()
    fields = dict(
        predicted_value=dog_ml, bet_on_home=(bet_side == "HOME"), confidence=None,
        market_spread_open=None, market_spread_current=spread_current,
        predicted_at=datetime.utcnow(), model_version=version_tag,
    )
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(ModelPrediction(game_id=game_id, system_id=system_id, bet_type="moneyline", **fields))


def predict_upcoming_week(week: int = None, season: int = CURRENT_SEASON, write_to_db: bool = True):
    db = SessionLocal()

    system = db.query(BettingSystem).filter(
        BettingSystem.system_name == SYSTEM_DB_NAME, BettingSystem.bet_type == "moneyline"
    ).first()
    if write_to_db and system is None:
        print(f"WARNING: '{SYSTEM_DB_NAME}' not registered - skipping DB writes.")
        write_to_db = False

    cache_rows = db.query(GameFeatureCache).join(Game).filter(Game.season == season).all()
    if week is not None:
        cache_rows = [r for r in cache_rows if r.features.get("week") == week]

    print(f"Found {len(cache_rows)} cached games for {season}"
          f"{f' week {week}' if week else ''} (from game_feature_cache)")

    game_ids = [r.game_id for r in cache_rows]
    all_book_lines = get_live_book_lines_batch(game_ids, db)
    games_by_id = {g.id: g for g in db.query(Game).filter(Game.id.in_(game_ids)).all()}

    written = 0
    all_picks = []

    for row in cache_rows:
        book_lines = all_book_lines.get(row.game_id, {})
        if not book_lines:
            continue

        game = games_by_id[row.game_id]
        matchup = f"{game.away_team_name} @ {game.home_team_name}"

        qualifying = evaluate_game(row.features, book_lines)
        for book, bet_side, dog_ml, spread_current in qualifying:
            all_picks.append((matchup, book, row.features["week"], bet_side, dog_ml, spread_current))
            if write_to_db:
                _upsert_prediction(db, row.game_id, system.id, book, dog_ml, spread_current, bet_side)
                written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows\n")

    print(f"{'='*70}\n{SYSTEM_DB_NAME} - qualifying picks by book ({len(all_picks)})\n{'='*70}")
    for matchup, book, wk, side, ml, spread in sorted(all_picks, key=lambda x: x[5]):
        print(f"  {matchup} [{book}] (wk {wk}) - BET {side} dog ML={ml:+.0f} (current spread: {spread:+.1f})")
    if not all_picks:
        print("  No qualifying picks this week.")

    db.close()


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else None
    predict_upcoming_week(week=week)