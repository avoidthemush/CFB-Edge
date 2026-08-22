"""
Returns EVERY FBS-vs-FBS game for a given week, each with whatever
qualifying picks exist for it (empty array if none) - restructured
(Aug 2026) from the original version, which started from
model_predictions and could therefore never include a game with zero
qualifying signals. Now starts from games and attaches picks, so the
dashboard can show the full week's slate with signals overlaid, not
just the subset that already qualifies.
"""
from fastapi import APIRouter, Query
from app.db import SessionLocal
from app.models import ModelPrediction, BettingSystem, Game, Venue, WeatherSnapshot, TeamRecentForm, Team
from app.config import CURRENT_SEASON

router = APIRouter()


def to_utc_iso(dt):
    return dt.isoformat() + "Z" if dt else None


def derive_weather_condition(temp_f, wind_mph, precip_prob):
    if temp_f is None and wind_mph is None and precip_prob is None:
        return None
    if precip_prob is not None and precip_prob >= 50:
        if temp_f is not None and temp_f <= 34:
            return "snow"
        return "rain"
    if wind_mph is not None and wind_mph >= 20:
        return "windy"
    if temp_f is not None and temp_f <= 34:
        return "cold"
    return "clear"


def get_season_records_batch(team_ids, season, db):
    games = db.query(Game).filter(
        (Game.home_team_id.in_(team_ids)) | (Game.away_team_id.in_(team_ids)),
        Game.season == season, Game.completed == True,
        Game.home_points.isnot(None), Game.away_points.isnot(None),
    ).all()

    records = {tid: {"wins": 0, "losses": 0} for tid in team_ids}
    for g in games:
        if g.home_team_id in records:
            if g.home_points > g.away_points:
                records[g.home_team_id]["wins"] += 1
            else:
                records[g.home_team_id]["losses"] += 1
        if g.away_team_id in records:
            if g.away_points > g.home_points:
                records[g.away_team_id]["wins"] += 1
            else:
                records[g.away_team_id]["losses"] += 1

    return {tid: f"{r['wins']}-{r['losses']}" for tid, r in records.items()}


def get_recent_form_summaries_batch(team_ids, db):
    forms = db.query(TeamRecentForm).filter(TeamRecentForm.team_id.in_(team_ids)).all()
    result = {}
    for f in forms:
        result[f.team_id] = {
            "games_counted": f.games_counted,
            "ats": f"{f.ats_wins}-{f.ats_losses}-{f.ats_pushes}",
            "ou": f"{f.ou_overs}-{f.ou_unders}-{f.ou_pushes}",
            "su": f"{f.su_wins}-{f.su_losses}",
        }
    return result


def serialize_pick(pred, system):
    return {
        "bet_type": pred.bet_type,
        "system_name": system.system_name,
        "system_category": system.category,
        "book": pred.model_version.split(":")[-1] if ":" in (pred.model_version or "") else None,
        "bet_on_home": pred.bet_on_home,
        "predicted_value": pred.predicted_value,
        "confidence": pred.confidence,
        "market_line_open": pred.market_spread_open,
        "market_line_current": pred.market_spread_current,
        "predicted_at": to_utc_iso(pred.predicted_at),
        "system_historical_win_rate": system.pooled_win_rate,
        "system_historical_roi": system.pooled_roi,
        "system_historical_bootstrap": system.bootstrap_pct_profitable,
    }


@router.get("/week/{week}")
def get_week_games(week: int, season: int = Query(default=CURRENT_SEASON)):
    db = SessionLocal()
    try:
        fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}
        all_games = db.query(Game).filter(Game.season == season, Game.week == week).all()
        games = [g for g in all_games if g.home_team_id in fbs_team_ids and g.away_team_id in fbs_team_ids]
        game_ids = [g.id for g in games]

        pred_rows = (
            db.query(ModelPrediction, BettingSystem)
            .join(BettingSystem, ModelPrediction.system_id == BettingSystem.id)
            .filter(ModelPrediction.game_id.in_(game_ids))
            .all()
        )
        picks_by_game = {}
        for pred, system in pred_rows:
            picks_by_game.setdefault(pred.game_id, []).append(serialize_pick(pred, system))

        venues_by_id = {v.id: v for v in db.query(Venue).filter(
            Venue.id.in_([g.venue_id for g in games if g.venue_id])
        ).all()}
        weather_by_game = {
            w.game_id: w for w in db.query(WeatherSnapshot).filter(
                WeatherSnapshot.game_id.in_(game_ids)
            ).all()
        }

        team_ids = list({g.home_team_id for g in games} | {g.away_team_id for g in games})
        season_records = get_season_records_batch(team_ids, season, db)
        recent_forms = get_recent_form_summaries_batch(team_ids, db)

        results = []
        for game in games:
            venue = venues_by_id.get(game.venue_id)
            weather = weather_by_game.get(game.id)

            results.append({
                "matchup": f"{game.away_team_name} @ {game.home_team_name}",
                "kickoff": to_utc_iso(game.start_date),
                "venue": {
                    "name": venue.name if venue else None,
                    "city": venue.city if venue else None,
                    "state": venue.state if venue else None,
                    "is_dome": venue.is_dome if venue else None,
                } if venue else None,
                "weather": {
                    "temp_f": weather.temp_f if weather else None,
                    "wind_mph": weather.wind_mph if weather else None,
                    "precip_prob": weather.precip_prob if weather else None,
                    "condition": derive_weather_condition(
                        weather.temp_f if weather else None,
                        weather.wind_mph if weather else None,
                        weather.precip_prob if weather else None,
                    ) if weather else None,
                } if weather else None,
                "away_team": {
                    "name": game.away_team_name,
                    "season_record": season_records.get(game.away_team_id),
                    "recent_form": recent_forms.get(game.away_team_id),
                },
                "home_team": {
                    "name": game.home_team_name,
                    "season_record": season_records.get(game.home_team_id),
                    "recent_form": recent_forms.get(game.home_team_id),
                },
                "picks": picks_by_game.get(game.id, []),
            })

        results.sort(key=lambda g: g["kickoff"] or "")

        return {
            "season": season, "week": week,
            "game_count": len(results),
            "games_with_signal": sum(1 for g in results if g["picks"]),
            "games": results,
        }
    finally:
        db.close()