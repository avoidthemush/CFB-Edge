"""
Runs the saved production Spread model against real, upcoming FBS-vs-FBS
games, evaluating EACH book (DraftKings, FanDuel) separately since they
can disagree on the line.

Aug 2026 fixes: (1) FBS-only filter added - live query previously pulled
ALL games including FCS opponents, but the model was only ever trained/
validated on FBS-vs-FBS games. (2) FeatureCache built once and reused,
live book lines checked first before full feature-building - fixes a
45+ min runtime caused by rebuilding expensive lookups (coach H2H index)
from scratch per game. (3) Spread line now shown in output for every pick.
"""
import json
import joblib
import pandas as pd
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction, Team
from app.features.build_game_features import build_game_features
from app.features.get_game_line import get_live_book_lines
from app.features.feature_cache import FeatureCache
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

    X = pd.DataFrame([row])[feature_cols]
    X_imputed = imputer.transform(X)
    X_scaled = scaler.transform(X_imputed)
    prob_home_covers = model.predict_proba(X_scaled)[0][1]
    return float(prob_home_covers)


def evaluate_for_book(prob_home_covers, week, neutral_site, spread_open):
    bet_on_home = prob_home_covers >= 0.5
    confidence = prob_home_covers if bet_on_home else (1 - prob_home_covers)
    is_underdog_bet = (
        (bet_on_home and spread_open > 0) or
        (not bet_on_home and spread_open < 0)
    )
    qualifies_general = confidence >= GENERAL_CONFIDENCE_THRESHOLD
    qualifies_focused = (
        qualifies_general and week >= FOCUSED_MIN_WEEK and
        is_underdog_bet and neutral_site != True
    )
    return {
        "bet_on_home": bool(bet_on_home), "confidence": round(confidence, 4),
        "is_underdog_bet": bool(is_underdog_bet), "spread_open": spread_open,
        "qualifies_general_model": bool(qualifies_general),
        "qualifies_focused_value_mid_season_dog": bool(qualifies_focused),
    }


def predict_game(game, model, scaler, imputer, feature_cols, db, cache):
    book_lines = get_live_book_lines(game.id, db)
    if not book_lines:
        return {"game_id": game.id, "status": "no_market_line"}

    features = build_game_features(game.id, db=db, cache=cache, game=game)
    if features is None:
        return None

    prob_home_covers = get_model_prediction(features, model, scaler, imputer, feature_cols)

    per_book = {}
    for book, line in book_lines.items():
        if line.spread_open is None:
            continue
        per_book[book] = evaluate_for_book(
            prob_home_covers, features["week"], features.get("neutral_site"), line.spread_open
        )

    return {
        "game_id": game.id, "status": "predicted", "week": int(features["week"]),
        "prob_home_covers": round(prob_home_covers, 4), "per_book": per_book,
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
        market_spread_current=result["spread_open"], predicted_at=datetime.utcnow(),
        model_version=version_tag,
    )
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(ModelPrediction(game_id=game_id, system_id=system_id, bet_type=bet_type, **fields))


def predict_upcoming_week(week: int, season: int = CURRENT_SEASON, write_to_db: bool = True):
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

    fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}
    all_games = db.query(Game).filter(Game.season == season, Game.week == week, Game.completed == False).all()
    games = [g for g in all_games if g.home_team_id in fbs_team_ids and g.away_team_id in fbs_team_ids]
    print(f"Found {len(all_games)} total games, {len(games)} FBS-vs-FBS for {season} week {week}")

    print("Building feature cache (one-time cost, reused across all games)...")
    cache = FeatureCache(start_year=season, end_year=season)
    print()

    written = 0
    general_picks, focused_picks = [], []

    for game in games:
        result = predict_game(game, model, scaler, imputer, feature_cols, db, cache)
        if result is None or result["status"] != "predicted":
            continue

        matchup = f"{game.away_team_name} @ {game.home_team_name}"
        for book, r in result["per_book"].items():
            side = "HOME" if r["bet_on_home"] else "AWAY"
            if r["qualifies_general_model"]:
                general_picks.append((matchup, book, result["week"], side, r["confidence"], r["qualifies_focused_value_mid_season_dog"], r["spread_open"]))
                if write_to_db:
                    _upsert_prediction(db, game.id, general_system.id, "spread", book, r, MODEL_PATH)
                    written += 1
            if r["qualifies_focused_value_mid_season_dog"]:
                focused_picks.append((matchup, book, result["week"], side, r["confidence"], r["spread_open"]))
                if write_to_db:
                    _upsert_prediction(db, game.id, focused_system.id, "spread", book, r, MODEL_PATH)
                    written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows\n")

    print(f"{'='*70}\nGENERAL MODEL - qualifying picks by book ({len(general_picks)})\n{'='*70}")
    for matchup, book, wk, side, conf, also_focused, spread in sorted(general_picks, key=lambda x: -x[4]):
        flag = f" [ALSO: {FOCUSED_TAG_NAME}]" if also_focused else ""
        print(f"  {matchup} [{book}] (wk {wk}) - {side} @ {conf*100:.1f}% (spread: {spread:+.1f}){flag}")
    if not general_picks:
        print("  No qualifying picks this week.")

    print(f"\n{'='*70}\nFOCUSED VALUE - tag '{FOCUSED_TAG_NAME}' - qualifying picks by book ({len(focused_picks)})\n{'='*70}")
    for matchup, book, wk, side, conf, spread in sorted(focused_picks, key=lambda x: -x[4]):
        print(f"  {matchup} [{book}] (wk {wk}) - {side} @ {conf*100:.1f}% (spread: {spread:+.1f})")
    if not focused_picks:
        print("  No qualifying picks this week.")

    db.close()


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    predict_upcoming_week(week=week)