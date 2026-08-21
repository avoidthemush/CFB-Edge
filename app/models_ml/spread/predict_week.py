"""
Runs the saved production Spread model using CACHED features and
BATCHED live odds lookups. Qualification (underdog/favorite status) is
checked against the CURRENT line, not the opening line - a live betting
decision must be evaluated against the price actually available right
now at DraftKings/FanDuel, not a stale historical reference. Both
values are still recorded for reference.
"""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

import json
import joblib
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction, GameFeatureCache
from app.features.get_game_line import get_live_book_lines_batch
from app.config import CURRENT_SEASON

GENERAL_CONFIDENCE_THRESHOLD = 0.60
FOCUSED_MIN_WEEK = 5
FOCUSED_TAG_NAME = "Mid-Season Dog"

MODEL_PATH = "spread_production_model.joblib"
SCALER_PATH = "spread_production_scaler.joblib"
IMPUTER_PATH = "spread_production_imputer.joblib"
FEATURES_PATH = "spread_production_features.json"


def load_production_model():
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    imputer = joblib.load(IMPUTER_PATH)
    with open(FEATURES_PATH) as f:
        feature_cols = json.load(f)
    return model, scaler, imputer, feature_cols


def get_model_prediction(features, model, scaler, imputer, feature_cols):
    bool_cols = ["home_is_new_coach_year", "away_is_new_coach_year", "neutral_site", "is_dome"]
    row = {}
    for col in feature_cols:
        val = features.get(col)
        if col in bool_cols and val is not None:
            val = 1 if val else 0
        row[col] = val

    X = [[row[col] for col in feature_cols]]
    X_imputed = imputer.transform(X)
    X_scaled = scaler.transform(X_imputed)
    return float(model.predict_proba(X_scaled)[0][1])


def evaluate_for_book(prob_home_covers, week, neutral_site, spread_current, spread_open):
    """
    Qualification uses the CURRENT spread (spread_current) - a live
    betting decision must reflect the actual, presently-available price,
    not a stale opening number. spread_open is retained only for
    reference/record-keeping, not used in any qualification logic here.
    """
    bet_on_home = prob_home_covers >= 0.5
    confidence = prob_home_covers if bet_on_home else (1 - prob_home_covers)
    is_underdog_bet = (
        (bet_on_home and spread_current > 0) or
        (not bet_on_home and spread_current < 0)
    )
    qualifies_general = confidence >= GENERAL_CONFIDENCE_THRESHOLD
    qualifies_focused = (
        qualifies_general and week >= FOCUSED_MIN_WEEK and
        is_underdog_bet and neutral_site != True
    )
    return {
        "bet_on_home": bool(bet_on_home), "confidence": round(confidence, 4),
        "is_underdog_bet": bool(is_underdog_bet),
        "spread_current": spread_current, "spread_open": spread_open,
        "qualifies_general_model": bool(qualifies_general),
        "qualifies_focused_value_mid_season_dog": bool(qualifies_focused),
    }


def _upsert_prediction(db, game_id, system_id, bet_type, book, result, model_version):
    version_tag = f"{model_version}:{book}"
    existing = db.query(ModelPrediction).filter(
        ModelPrediction.game_id == game_id, ModelPrediction.system_id == system_id,
        ModelPrediction.model_version == version_tag,
    ).first()
    fields = dict(
        predicted_value=result["confidence"], bet_on_home=result["bet_on_home"],
        confidence=result["confidence"], market_spread_open=result["spread_open"],
        market_spread_current=result["spread_current"], predicted_at=datetime.utcnow(),
        model_version=version_tag,
    )
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(ModelPrediction(game_id=game_id, system_id=system_id, bet_type=bet_type, **fields))


def predict_upcoming_week(week: int = None, season: int = CURRENT_SEASON, write_to_db: bool = True):
    db = SessionLocal()
    model, scaler, imputer, feature_cols = load_production_model()

    general_system = db.query(BettingSystem).filter(
        BettingSystem.system_name == "General Model", BettingSystem.bet_type == "spread"
    ).first()
    focused_system = db.query(BettingSystem).filter(
        BettingSystem.system_name == FOCUSED_TAG_NAME, BettingSystem.bet_type == "spread"
    ).first()
    if write_to_db and (general_system is None or focused_system is None):
        print("WARNING: betting_systems not seeded - skipping DB writes.")
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
    general_picks, focused_picks = [], []

    for row in cache_rows:
        book_lines = all_book_lines.get(row.game_id, {})
        if not book_lines:
            continue

        prob_home_covers = get_model_prediction(row.features, model, scaler, imputer, feature_cols)
        game = games_by_id[row.game_id]
        matchup = f"{game.away_team_name} @ {game.home_team_name}"

        for book, line in book_lines.items():
            if line.spread is None:
                continue
            r = evaluate_for_book(prob_home_covers, row.features["week"], row.features.get("neutral_site"), line.spread, line.spread_open)
            side = "HOME" if r["bet_on_home"] else "AWAY"

            if r["qualifies_general_model"]:
                general_picks.append((matchup, book, row.features["week"], side, r["confidence"], r["qualifies_focused_value_mid_season_dog"], r["spread_current"]))
                if write_to_db:
                    _upsert_prediction(db, row.game_id, general_system.id, "spread", book, r, MODEL_PATH)
                    written += 1
            if r["qualifies_focused_value_mid_season_dog"]:
                focused_picks.append((matchup, book, row.features["week"], side, r["confidence"], r["spread_current"]))
                if write_to_db:
                    _upsert_prediction(db, row.game_id, focused_system.id, "spread", book, r, MODEL_PATH)
                    written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows\n")

    print(f"{'='*70}\nGENERAL MODEL - qualifying picks by book ({len(general_picks)})\n{'='*70}")
    for matchup, book, wk, side, conf, also_focused, spread in sorted(general_picks, key=lambda x: -x[4]):
        flag = f" [ALSO: {FOCUSED_TAG_NAME}]" if also_focused else ""
        print(f"  {matchup} [{book}] (wk {wk}) - {side} @ {conf*100:.1f}% (current spread: {spread:+.1f}){flag}")
    if not general_picks:
        print("  No qualifying picks this week.")

    print(f"\n{'='*70}\nFOCUSED VALUE - tag '{FOCUSED_TAG_NAME}' - qualifying picks by book ({len(focused_picks)})\n{'='*70}")
    for matchup, book, wk, side, conf, spread in sorted(focused_picks, key=lambda x: -x[4]):
        print(f"  {matchup} [{book}] (wk {wk}) - {side} @ {conf*100:.1f}% (current spread: {spread:+.1f})")
    if not focused_picks:
        print("  No qualifying picks this week.")

    db.close()


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else None
    predict_upcoming_week(week=week)