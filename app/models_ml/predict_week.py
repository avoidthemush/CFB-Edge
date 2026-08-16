"""
Runs the saved production Spread model against real, upcoming games and
reports BOTH approved systems per game:
- General Model: confidence>=0.60, no restrictions - applies to every game
- Focused Value: + week>=5, underdog-only, non-neutral-site - a stricter
  subset of General Model's picks

Both systems share the SAME trained model/prediction - Focused Value is
never a separate model, just additional filters on the same output.

Uses get_game_line.py's CFBD-then-Odds-API fallback, so this works
identically whether a game has CFBD historical-style data or only our
own live Odds API polling (DK/FanDuel via LIVE_BOOK_PRIORITY).
"""
import json
import joblib
import pandas as pd
from app.db import SessionLocal
from app.models import Game
from app.features.build_game_features import build_game_features
from app.config import CURRENT_SEASON

GENERAL_CONFIDENCE_THRESHOLD = 0.60
FOCUSED_MIN_WEEK = 5

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
    qualifies_focused = (
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
        "qualifies_focused_value": bool(qualifies_focused),
    }


def predict_upcoming_week(week: int, season: int = CURRENT_SEASON):
    db = SessionLocal()
    model, scaler, imputer, feature_cols = load_production_model()

    games = db.query(Game).filter(
        Game.season == season, Game.week == week, Game.completed == False,
    ).all()

    print(f"Found {len(games)} upcoming games for {season} week {week}\n")

    results = []
    for game in games:
        result = predict_game(game.id, model, scaler, imputer, feature_cols, db)
        if result is None:
            continue
        result["matchup"] = f"{game.away_team_name} @ {game.home_team_name}"
        results.append(result)

    predicted = [r for r in results if r["status"] == "predicted"]
    no_line = [r for r in results if r["status"] == "no_market_line"]
    general_picks = [r for r in predicted if r["qualifies_general_model"]]
    focused_picks = [r for r in predicted if r["qualifies_focused_value"]]

    print(f"Games with no market line yet (skipped): {len(no_line)}")
    print(f"Games predicted: {len(predicted)}")

    print(f"\n{'='*70}")
    print(f"GENERAL MODEL - all qualifying picks ({len(general_picks)})")
    print(f"{'='*70}")
    for r in sorted(general_picks, key=lambda x: -x["confidence"]):
        side = "HOME" if r["bet_on_home"] else "AWAY"
        focused_flag = " [ALSO Focused Value]" if r["qualifies_focused_value"] else ""
        print(f"  {r['matchup']} (wk {r['week']}) - {side} @ {r['confidence']*100:.1f}%{focused_flag}")
    if not general_picks:
        print("  No qualifying picks this week.")

    print(f"\n{'='*70}")
    print(f"FOCUSED VALUE - qualifying picks ({len(focused_picks)})")
    print(f"{'='*70}")
    for r in sorted(focused_picks, key=lambda x: -x["confidence"]):
        side = "HOME" if r["bet_on_home"] else "AWAY"
        print(f"  {r['matchup']} (wk {r['week']}) - {side} @ {r['confidence']*100:.1f}%")
    if not focused_picks:
        print("  No qualifying picks this week.")

    db.close()
    return results


if __name__ == "__main__":
    predict_upcoming_week(week=5)