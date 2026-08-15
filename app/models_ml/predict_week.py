"""
Runs the saved production Spread model against real, upcoming games -
the first time this pipeline has ever been pointed at a game with no
known outcome. Applies the LOCKED "Mid-Season Value Dog" system rule
(week>=5, underdog-only, confidence>=0.60, non-neutral-site) and clearly
flags which games qualify as a real system pick vs. which don't.

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

MIN_WEEK = 5
CONFIDENCE_THRESHOLD = 0.60

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
        return {"game_id": game_id, "status": "no_market_line", "features": features}

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

    qualifies = (
        features["week"] >= MIN_WEEK and
        confidence >= CONFIDENCE_THRESHOLD and
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
        "qualifies_mid_season_value_dog": bool(qualifies),
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

    no_line = [r for r in results if r["status"] == "no_market_line"]
    predicted = [r for r in results if r["status"] == "predicted"]
    qualifying = [r for r in predicted if r["qualifies_mid_season_value_dog"]]

    print(f"Games with no market line yet (skipped): {len(no_line)}")
    for r in no_line:
        pass  # matchup not attached for no_market_line case above; fine to skip detail here

    print(f"Games predicted: {len(predicted)}")
    print(f"\n{'='*70}")
    print(f"MID-SEASON VALUE DOG - QUALIFYING PICKS ({len(qualifying)})")
    print(f"{'='*70}")
    for r in sorted(qualifying, key=lambda x: -x["confidence"]):
        side = "HOME" if r["bet_on_home"] else "AWAY"
        print(f"\n{r['matchup']} (week {r['week']})")
        print(f"  Bet: {side} | Confidence: {r['confidence']*100:.1f}%")
        print(f"  Market spread (open): {r['market_spread_open']} | (current): {r['market_spread_current']}")

    if not qualifying:
        print("\n  No qualifying picks this week.")

    db.close()
    return results


if __name__ == "__main__":
    predict_upcoming_week(week=5)