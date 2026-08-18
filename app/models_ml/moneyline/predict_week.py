"""
Runs the approved Unranked Favorite Dog system against real, upcoming
FBS-vs-FBS games, evaluating EACH book (DraftKings, FanDuel) separately
since moneylines can genuinely differ between books - same discipline
as Spread and Total.

No trained model needed - this is pure rule logic: bet the underdog's
moneyline when (1) spread <= 10 and (2) the favorite is NOT a ranked
(AP Top 25) team. Validated: 5/5 years profitable both directions,
pooled ROI +6.3%, bootstrap 96.6% profitable. See MONEYLINE_FEATURE_LOG.md.
"""
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction, Team
from app.features.build_game_features import build_game_features
from app.features.get_game_line import get_live_book_lines
from app.features.feature_cache import FeatureCache
from app.config import CURRENT_SEASON

MAX_DOG_SPREAD = 10
SYSTEM_DB_NAME = "Unranked Favorite Dog"


def evaluate_game(features, book_lines):
    """Returns list of (book, bet_side, dog_ml, spread_open) for qualifying books."""
    results = []
    for book, line in book_lines.items():
        if line.spread_open is None or line.spread_open == 0:
            continue

        home_is_dog = line.spread_open > 0
        dog_spread_size = abs(line.spread_open)
        if dog_spread_size > MAX_DOG_SPREAD:
            continue

        favorite_is_ranked = features.get("away_is_ranked") if home_is_dog else features.get("home_is_ranked")
        if favorite_is_ranked is None or favorite_is_ranked == 1:
            continue

        dog_ml = line.home_moneyline if home_is_dog else line.away_moneyline
        if dog_ml is None:
            continue

        bet_side = "HOME" if home_is_dog else "AWAY"
        results.append((book, bet_side, dog_ml, line.spread_open))

    return results


def predict_game(game, db, cache):
    book_lines = get_live_book_lines(game.id, db)
    if not book_lines:
        return {"game_id": game.id, "status": "no_market_line"}

    features = build_game_features(game.id, db=db, cache=cache, game=game)
    if features is None:
        return None

    qualifying = evaluate_game(features, book_lines)
    return {"game_id": game.id, "status": "predicted", "week": int(features["week"]), "qualifying": qualifying}


def _upsert_prediction(db, game_id, system_id, book, dog_ml, spread_open, bet_side):
    version_tag = f"unranked_favorite_dog_rule:{book}"
    existing = db.query(ModelPrediction).filter(
        ModelPrediction.game_id == game_id, ModelPrediction.system_id == system_id,
        ModelPrediction.model_version == version_tag,
    ).first()
    fields = dict(
        predicted_value=dog_ml, bet_on_home=(bet_side == "HOME"), confidence=None,
        market_spread_open=spread_open, market_spread_current=spread_open,
        predicted_at=datetime.utcnow(), model_version=version_tag,
    )
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(ModelPrediction(game_id=game_id, system_id=system_id, bet_type="moneyline", **fields))


def predict_upcoming_week(week: int, season: int = CURRENT_SEASON, write_to_db: bool = True):
    db = SessionLocal()

    system = db.query(BettingSystem).filter(
        BettingSystem.system_name == SYSTEM_DB_NAME, BettingSystem.bet_type == "moneyline"
    ).first()
    if write_to_db and system is None:
        print(f"WARNING: '{SYSTEM_DB_NAME}' not registered in betting_systems - skipping DB writes.")
        write_to_db = False

    fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}
    all_games = db.query(Game).filter(Game.season == season, Game.week == week, Game.completed == False).all()
    games = [g for g in all_games if g.home_team_id in fbs_team_ids and g.away_team_id in fbs_team_ids]
    print(f"Found {len(all_games)} total games, {len(games)} FBS-vs-FBS for {season} week {week}")

    print("Building feature cache...")
    cache = FeatureCache(start_year=season, end_year=season)
    print()

    written = 0
    all_picks = []

    for game in games:
        result = predict_game(game, db, cache)
        if result is None or result["status"] != "predicted":
            continue

        matchup = f"{game.away_team_name} @ {game.home_team_name}"
        for book, bet_side, dog_ml, spread_open in result["qualifying"]:
            all_picks.append((matchup, book, result["week"], bet_side, dog_ml, spread_open))
            if write_to_db:
                _upsert_prediction(db, game.id, system.id, book, dog_ml, spread_open, bet_side)
                written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows\n")

    print(f"{'='*70}\n{SYSTEM_DB_NAME} - qualifying picks by book ({len(all_picks)})\n{'='*70}")
    for matchup, book, wk, side, ml, spread in sorted(all_picks, key=lambda x: x[5]):
        print(f"  {matchup} [{book}] (wk {wk}) - BET {side} dog ML={ml:+.0f} (spread was {spread:+.1f})")
    if not all_picks:
        print("  No qualifying picks this week.")

    db.close()


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    predict_upcoming_week(week=week)