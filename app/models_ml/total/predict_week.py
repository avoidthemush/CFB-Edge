"""
Runs Total's production Market Deviation systems against real, upcoming
games, writes qualifying predictions to model_predictions (tagged by
system), and reports each system's picks per game.

Unlike Spread, there's no single "confidence" score - each system either
fires (game's deviation is in the extreme percentile, using cutoffs
fixed from the baseline season) or doesn't. A game can qualify for
multiple systems simultaneously.
"""
import json
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction
from app.features.build_game_features import build_game_features
from app.config import CURRENT_SEASON

ARTIFACTS_PATH = "total_production_systems.json"

SYSTEM_DB_NAMES = {
    "pace_deviation": "Pace Deviation",
    "field_position_deviation": "Field Position Deviation",
    "travel_deviation": "Travel Deviation",
    "wind_deviation": "Wind Deviation",
    "pace_deviation_home_favorite_tag": "Pace Deviation Home Favorite",
}

DIMENSIONS = {
    "pace_deviation": lambda f: f.get("home_off_plays_per_drive", 0) + f.get("away_off_plays_per_drive", 0)
        if f.get("home_off_plays_per_drive") is not None and f.get("away_off_plays_per_drive") is not None else None,
    "field_position_deviation": lambda f: f.get("home_off_field_position_predicted_points", 0) + f.get("away_off_field_position_predicted_points", 0)
        if f.get("home_off_field_position_predicted_points") is not None and f.get("away_off_field_position_predicted_points") is not None else None,
    "travel_deviation": lambda f: (f.get("home_travel_distance") or 0) + (f.get("away_travel_distance") or 0),
    "wind_deviation": lambda f: f.get("wind_mph"),
    "pace_deviation_home_favorite_tag": lambda f: f.get("home_off_plays_per_drive", 0) + f.get("away_off_plays_per_drive", 0)
        if f.get("home_off_plays_per_drive") is not None and f.get("away_off_plays_per_drive") is not None else None,
}

REQUIRES_HOME_FAVORITE = {"wind_deviation", "pace_deviation_home_favorite_tag"}


def load_artifacts():
    with open(ARTIFACTS_PATH) as f:
        return json.load(f)


def get_bucket_avg(bucket_val, bins, bucket_avg):
    import bisect
    idx = bisect.bisect_right(bins, bucket_val) - 1
    idx = max(0, min(idx, len(bins) - 2))
    return bucket_avg.get(str(idx))


def evaluate_system(name, config, features):
    if name in REQUIRES_HOME_FAVORITE:
        spread_open = features.get("market_spread_open")
        if spread_open is None or spread_open >= 0:
            return None  # not a home favorite, this system doesn't apply

    bucket_val = DIMENSIONS[name](features)
    if bucket_val is None:
        return None

    market_total_open = features.get("market_total_open")
    if market_total_open is None:
        return None

    expected_total = get_bucket_avg(bucket_val, config["bins"], config["bucket_avg"])
    if expected_total is None:
        return None

    deviation = market_total_open - expected_total

    if deviation <= config["low_cutoff"]:
        return {"fires": True, "bet": "OVER", "deviation": deviation, "expected_total": expected_total}
    elif deviation >= config["high_cutoff"]:
        return {"fires": True, "bet": "UNDER", "deviation": deviation, "expected_total": expected_total}
    return {"fires": False, "deviation": deviation, "expected_total": expected_total}


def predict_game(game_id, artifacts, db):
    features = build_game_features(game_id, db=db)
    if features is None:
        return None
    if features.get("market_total_open") is None:
        return {"game_id": game_id, "status": "no_market_line"}

    results = {}
    for name, config in artifacts.items():
        results[name] = evaluate_system(name, config, features)

    return {"game_id": game_id, "status": "predicted", "week": int(features["week"]),
            "market_total_open": features["market_total_open"], "results": results}


def _upsert_prediction(db, game_id, system_id, bet_type, bet_direction, deviation, market_total_open):
    existing = db.query(ModelPrediction).filter(
        ModelPrediction.game_id == game_id, ModelPrediction.system_id == system_id
    ).first()

    fields = dict(
        predicted_value=deviation,
        bet_on_home=None,  # not applicable for Total - bet_direction (OVER/UNDER) stored separately if schema extended
        confidence=None,
        market_spread_open=None,
        market_spread_current=None,
        predicted_at=datetime.utcnow(),
        model_version=ARTIFACTS_PATH,
    )
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
    else:
        db.add(ModelPrediction(game_id=game_id, system_id=system_id, bet_type=bet_type, **fields))


def predict_upcoming_week(week: int, season: int = CURRENT_SEASON, write_to_db: bool = True):
    db = SessionLocal()
    artifacts = load_artifacts()

    system_ids = {}
    for name, db_name in SYSTEM_DB_NAMES.items():
        system = db.query(BettingSystem).filter(
            BettingSystem.system_name == db_name, BettingSystem.bet_type == "total"
        ).first()
        system_ids[name] = system.id if system else None

    games = db.query(Game).filter(
        Game.season == season, Game.week == week, Game.completed == False,
    ).all()

    print(f"Found {len(games)} upcoming games for {season} week {week}\n")

    all_picks = {name: [] for name in artifacts}
    written = 0

    for game in games:
        result = predict_game(game.id, artifacts, db)
        if result is None or result["status"] != "predicted":
            continue

        matchup = f"{game.away_team_name} @ {game.home_team_name}"
        for name, r in result["results"].items():
            if r and r.get("fires"):
                all_picks[name].append((matchup, result["week"], r["bet"], r["deviation"], result["market_total_open"]))
                if write_to_db and system_ids.get(name):
                    _upsert_prediction(db, game.id, system_ids[name], "total", r["bet"], r["deviation"], result["market_total_open"])
                    written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows to model_predictions\n")

    for name, db_name in SYSTEM_DB_NAMES.items():
        picks = all_picks[name]
        print(f"{'='*70}\n{db_name} - qualifying picks ({len(picks)})\n{'='*70}")
        for matchup, wk, bet, dev, total in sorted(picks, key=lambda x: -abs(x[3])):
            print(f"  {matchup} (wk {wk}) - {bet} {total} (deviation {dev:+.1f})")
        if not picks:
            print("  No qualifying picks this week.")
        print()

    db.close()


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    predict_upcoming_week(week=week)