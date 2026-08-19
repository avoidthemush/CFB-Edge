"""
Runs Total's production Market Deviation systems using CACHED features
(game_feature_cache, refreshed weekly) and BATCHED live odds lookups
(one query for the whole slate, not one per game) - both changes
confirmed via real timing to matter (cache: ~2min -> ~4.5s; batched
odds: ~17s -> near-instant for a 51-game slate, same fix applied to
Spread's predict_week.py).
"""
import json
import bisect
from datetime import datetime
from app.db import SessionLocal
from app.models import Game, BettingSystem, ModelPrediction, GameFeatureCache
from app.features.get_game_line import get_live_book_lines_batch
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


def evaluate_system(name, config, cached_features, market_total_open, spread_open):
    if name in REQUIRES_HOME_FAVORITE:
        if spread_open is None or spread_open >= 0:
            return None

    bucket_val = DIMENSIONS[name](cached_features)
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


def predict_upcoming_week(week: int = None, season: int = CURRENT_SEASON, write_to_db: bool = True):
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
        print(f"WARNING: not registered, picks won't be written: {missing_systems}\n")

    cache_rows = db.query(GameFeatureCache).join(Game).filter(Game.season == season).all()
    if week is not None:
        cache_rows = [r for r in cache_rows if r.features.get("week") == week]

    print(f"Found {len(cache_rows)} cached games for {season}"
          f"{f' week {week}' if week else ''} (from game_feature_cache)")

    game_ids = [r.game_id for r in cache_rows]
    all_book_lines = get_live_book_lines_batch(game_ids, db)
    games_by_id = {g.id: g for g in db.query(Game).filter(Game.id.in_(game_ids)).all()}

    all_picks = {name: [] for name in artifacts}
    written = 0

    for row in cache_rows:
        book_lines = all_book_lines.get(row.game_id, {})
        if not book_lines:
            continue

        game = games_by_id[row.game_id]
        matchup = f"{game.away_team_name} @ {game.home_team_name}"

        for book, line in book_lines.items():
            if line.over_under is None:
                continue
            for name, config in artifacts.items():
                r = evaluate_system(name, config, row.features, line.over_under, line.spread_open)
                if r and r.get("fires"):
                    all_picks[name].append((matchup, book, row.features["week"], r["bet"], r["deviation"], line.over_under))
                    if write_to_db and system_ids.get(name):
                        _upsert_prediction(db, row.game_id, system_ids[name], "total", book, r, line.over_under, ARTIFACTS_PATH)
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
    week = int(sys.argv[1]) if len(sys.argv) > 1 else None
    predict_upcoming_week(week=week)