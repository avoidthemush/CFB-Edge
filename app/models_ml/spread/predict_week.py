"""
Runs the saved production Spread model against real, upcoming games,
WRITES qualifying predictions to model_predictions (tagged by system),
and reports both approved systems per game:
- General Model: confidence>=0.60, no restrictions
- Focused Value, tag "Mid-Season Dog": + week>=5, underdog-only, non-neutral

Both systems share the SAME trained model/prediction - Focused Value
tags are never separate models, just additional filters applied to the
same output. See SPREAD_FEATURE_LOG.md for full naming/validation history.

Re-running for the same week is safe - existing predictions for that
game+system are updated in place, not duplicated (checks by game_id +
system_id before inserting).

Known caveat: General Model has no week restriction and will produce
output for weeks 1-4, but calibration testing proved confidence is NOT
reliable in that window. Early-week General Model picks should be
treated with real skepticism until that's resolved.
"""
import json
import joblib
import pandas as pd
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction
from app.features.build_game_features import build_game_features
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


def predict_game(game_id, model, scaler, imputer, feature_cols, db):
    features = build_game_features(game_id, db=db)
    if features is None:
        return None

    if features.get("market_spread_open") is None:
        return {"game_id": game_id, "status": "no_market_line"}

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

    bet_on_home = prob_home_covers >= 0.5
    confidence = prob_home_covers if bet_on_home else (1 - prob_home_covers)

    market_spread_open = features["market_spread_open"]
    is_underdog_bet = (
        (bet_on_home and market_spread_open > 0) or
        (not bet_on_home and market_spread_open < 0)
    )

    qualifies_general = confidence >= GENERAL_CONFIDENCE_THRESHOLD
    qualifies_focused_mid_season_dog = (
        qualifies_general and
        features["week"] >= FOCUSED_MIN_WEEK and
        is_underdog_bet and
        features.get("neutral_site") != True
    )

    return {
        "game_id": game_id,
        "status": "predicted",
        "week": int(features["week"]),
        "prob_home_covers": round(float(prob_home_covers), 4),
        "bet_on_home": bool(bet_on_home),
        "confidence": round(float(confidence), 4),
        "is_underdog_bet": bool(is_underdog_bet),
        "market_spread_open": market_spread_open,
        "market_spread_current": features.get("market_spread"),
        "neutral_site": features.get("neutral_site"),
        "qualifies_general_model": bool(qualifies_general),
        "qualifies_focused_value_mid_season_dog": bool(qualifies_focused_mid_season_dog),
    }


def _upsert_prediction(db, game_id, system_id, bet_type, result, model_version):
    existing = db.query(ModelPrediction).filter(
        ModelPrediction.game_id == game_id, ModelPrediction.system_id == system_id
    ).first()

    fields = dict(
        predicted_value=result["prob_home_covers"],
        bet_on_home=result["bet_on_home"],
        confidence=result["confidence"],
        market_spread_open=result["market_spread_open"],
        market_spread_current=result["market_spread_current"],
        predicted_at=datetime.utcnow(),
        model_version=model_version,
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
        print("WARNING: betting_systems not seeded - run seed_betting_systems.py first. Skipping DB writes.")
        write_to_db = False

    games = db.query(Game).filter(
        Game.season == season, Game.week == week, Game.completed == False,
    ).all()

    print(f"Found {len(games)} upcoming games for {season} week {week}\n")

    results = []
    written = 0
    for game in games:
        result = predict_game(game.id, model, scaler, imputer, feature_cols, db)
        if result is None:
            continue
        result["matchup"] = f"{game.away_team_name} @ {game.home_team_name}"
        results.append(result)

        if write_to_db and result["status"] == "predicted":
            if result["qualifies_general_model"]:
                _upsert_prediction(db, game.id, general_system.id, "spread", result, MODEL_PATH)
                written += 1
            if result["qualifies_focused_value_mid_season_dog"]:
                _upsert_prediction(db, game.id, focused_system.id, "spread", result, MODEL_PATH)
                written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows to model_predictions\n")

    predicted = [r for r in results if r["status"] == "predicted"]
    no_line = [r for r in results if r["status"] == "no_market_line"]
    general_picks = [r for r in predicted if r["qualifies_general_model"]]
    focused_picks = [r for r in predicted if r["qualifies_focused_value_mid_season_dog"]]

    print(f"Games with no market line yet (skipped): {len(no_line)}")
    print(f"Games predicted: {len(predicted)}")

    print(f"\n{'='*70}")
    print(f"GENERAL MODEL - all qualifying picks ({len(general_picks)})")
    print(f"{'='*70}")
    for r in sorted(general_picks, key=lambda x: -x["confidence"]):
        side = "HOME" if r["bet_on_home"] else "AWAY"
        tag_flag = f" [ALSO: {FOCUSED_TAG_NAME}]" if r["qualifies_focused_value_mid_season_dog"] else ""
        print(f"  {r['matchup']} (wk {r['week']}) - {side} @ {r['confidence']*100:.1f}%{tag_flag}")
    if not general_picks:
        print("  No qualifying picks this week.")

    print(f"\n{'='*70}")
    print(f"FOCUSED VALUE - tag: '{FOCUSED_TAG_NAME}' - qualifying picks ({len(focused_picks)})")
    print(f"{'='*70}")
    for r in sorted(focused_picks, key=lambda x: -x["confidence"]):
        side = "HOME" if r["bet_on_home"] else "AWAY"
        print(f"  {r['matchup']} (wk {r['week']}) - {side} @ {r['confidence']*100:.1f}%")
    if not focused_picks:
        print("  No qualifying picks this week.")

    db.close()
    return results


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    predict_upcoming_week(week=week)