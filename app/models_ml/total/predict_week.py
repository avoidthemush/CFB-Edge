"""
Runs Total's production Market Deviation systems against real, upcoming
FBS-vs-FBS games, evaluating EACH book (DraftKings, FanDuel) separately.

Aug 2026 fixes: (1) FBS-only filter added - confirmed via real evidence
(Furman, NC A&T, Idaho State, North Alabama - all FCS - showing up in
Travel Deviation picks) that the live query was pulling non-FBS games
the systems were never validated against. (2) FeatureCache reused across
all games, live lines checked first. (3) All 5 systems now correctly
registered in betting_systems (Travel/Wind/Home-Favorite-tag were
missing from the seed script, causing a silent write failure where they
displayed correctly but never persisted to the database).
"""
import json
import bisect
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction, Team
from app.features.build_game_features import build_game_features
from app.features.get_game_line import get_live_book_lines
from app.features.feature_cache import FeatureCache
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
    "pace_deviation": lambda f: (f.get("home_off_plays_per_drive") + f.get("away_off_plays_per_drive"))
        if f.get("home_off_plays_per_drive") is not None and f.get("away_off_plays_per_drive") is not None else None,
    "field_position_deviation": lambda f: (f.get("home_off_field_position_predicted_points") + f.get("away_off_field_position_predicted_points"))
        if f.get("home_off_field_position_predicted_points") is not None and f.get("away_off_field_position_predicted_points") is not None else None,
    "travel_deviation": lambda f: (f.get("home_travel_distance") or 0) + (f.get("away_travel_distance") or 0),
    "wind_deviation": lambda f: f.get("wind_mph"),
    "pace_deviation_home_favorite_tag": lambda f: (f.get("home_off_plays_per_drive") + f.get("away_off_plays_per_drive"))
        if f.get("home_off_plays_per_drive") is not None and f.get("away_off_plays_per_drive") is not None else None,
}

REQUIRES_HOME_FAVORITE = {"wind_deviation", "pace_deviation_home_favorite_tag"}


def load_artifacts():
    with open(ARTIFACTS_PATH) as f:
        return json.load(f)


def get_bucket_avg(bucket_val, bins, bucket_avg):
    idx = bisect.bisect_right(bins, bucket_val) - 1
    idx = max(0, min(idx, len(bins) - 2))
    return bucket_avg.get(str(idx))


def evaluate_system(name, config, features, market_total_open, spread_open):
    if name in REQUIRES_HOME_FAVORITE:
        if spread_open is None or spread_open >= 0:
            return None

    bucket_val = DIMENSIONS[name](features)
    if bucket_val is None or market_total_open is None:
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


def predict_game(game, artifacts, db, cache):
    book_lines = get_live_book_lines(game.id, db)
    if not book_lines:
        return {"game_id": game.id, "status": "no_market_line"}

    features = build_game_features(game.id, db=db, cache=cache, game=game)
    if features is None:
        return None

    per_book = {}
    for book, line in book_lines.items():
        if line.over_under is None:
            continue
        results = {}
        for name, config in artifacts.items():
            results[name] = evaluate_system(name, config, features, line.over_under, line.spread_open)
        per_book[book] = {"market_total": line.over_under, "results": results}

    return {"game_id": game.id, "status": "predicted", "week": int(features["week"]), "per_book": per_book}


def _upsert_prediction(db, game_id, system_id, bet_type, book, r, market_total, model_version):
    version_tag = f"{model_version}:{book}"
    existing = db.query(ModelPrediction).filter(
        ModelPrediction.game_id == game_id, ModelPrediction.system_id == system_id,
        ModelPrediction.model_version == version_tag,
    ).first()
    fields = dict(
        predicted_value=r["deviation"], bet_on_home=None, confidence=None,
        market_spread_open=market_total, market_spread_current=market_total,
        predicted_at=datetime.utcnow(), model_version=version_tag,
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
    missing_systems = []
    for name, db_name in SYSTEM_DB_NAMES.items():
        system = db.query(BettingSystem).filter(
            BettingSystem.system_name == db_name, BettingSystem.bet_type == "total"
        ).first()
        system_ids[name] = system.id if system else None
        if system is None:
            missing_systems.append(db_name)

    if missing_systems:
        print(f"WARNING: these systems are not registered in betting_systems, picks will "
              f"display but NOT be written to the database: {missing_systems}\n")

    fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}
    all_games = db.query(Game).filter(Game.season == season, Game.week == week, Game.completed == False).all()
    games = [g for g in all_games if g.home_team_id in fbs_team_ids and g.away_team_id in fbs_team_ids]
    print(f"Found {len(all_games)} total games, {len(games)} FBS-vs-FBS for {season} week {week}")

    print("Building feature cache (one-time cost, reused across all games)...")
    cache = FeatureCache(start_year=season, end_year=season)
    print()

    all_picks = {name: [] for name in artifacts}
    written = 0

    for game in games:
        result = predict_game(game, artifacts, db, cache)
        if result is None or result["status"] != "predicted":
            continue

        matchup = f"{game.away_team_name} @ {game.home_team_name}"
        for book, book_data in result["per_book"].items():
            for name, r in book_data["results"].items():
                if r and r.get("fires"):
                    all_picks[name].append((matchup, book, result["week"], r["bet"], r["deviation"], book_data["market_total"]))
                    if write_to_db and system_ids.get(name):
                        _upsert_prediction(db, game.id, system_ids[name], "total", book, r, book_data["market_total"], ARTIFACTS_PATH)
                        written += 1

    if write_to_db:
        db.commit()
        print(f"Wrote/updated {written} prediction rows\n")

    for name, db_name in SYSTEM_DB_NAMES.items():
        picks = all_picks[name]
        print(f"{'='*70}\n{db_name} - qualifying picks by book ({len(picks)})\n{'='*70}")
        for matchup, book, wk, bet, dev, total in sorted(picks, key=lambda x: -abs(x[4])):
            print(f"  {matchup} [{book}] (wk {wk}) - {bet} {total} (deviation {dev:+.1f})")
        if not picks:
            print("  No qualifying picks this week.")
        print()

    db.close()


if __name__ == "__main__":
    import sys
    week = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    predict_upcoming_week(week=week)