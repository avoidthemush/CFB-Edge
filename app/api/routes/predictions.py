"""
Read-only endpoints for retrieving this week's qualifying picks,
enriched with venue, weather, both teams' recent form, and current
season record. Field naming is bet-type-neutral (market_line_* instead
of the old market_spread_* names, which incorrectly implied "spread"
even for Total rows).

TIMEZONE FIX (Aug 2026): timestamps are stored naive (no tzinfo) but
genuinely represent UTC. .isoformat() alone omits any zone marker,
which is ambiguous and gets misinterpreted by JS as local time -
confirmed real bug (a game's displayed kickoff was off by exactly the
Arizona UTC offset). Fixed by explicitly appending "Z" so every
timestamp this API returns is unambiguous UTC.
"""
from fastapi import APIRouter, Query
from app.db import SessionLocal
from app.models import ModelPrediction, BettingSystem, Game, Venue, WeatherSnapshot, TeamRecentForm, Team
from app.config import CURRENT_SEASON

router = APIRouter()


def to_utc_iso(dt):
    """Explicitly marks a naive-but-UTC datetime as UTC (appends 'Z') so no consumer can misinterpret it as local time."""
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


def get_season_record(team_id, season, db):
    games = db.query(Game).filter(
        (Game.home_team_id == team_id) | (Game.away_team_id == team_id),
        Game.season == season, Game.completed == True,
        Game.home_points.isnot(None), Game.away_points.isnot(None),
    ).all()

    wins = losses = 0
    for g in games:
        is_home = g.home_team_id == team_id
        team_points = g.home_points if is_home else g.away_points
        opp_points = g.away_points if is_home else g.home_points
        if team_points > opp_points:
            wins += 1
        else:
            losses += 1
    return f"{wins}-{losses}"


def get_recent_form_summary(team_id, db):
    form = db.query(TeamRecentForm).filter(TeamRecentForm.team_id == team_id).first()
    if form is None:
        return None
    return {
        "games_counted": form.games_counted,
        "ats": f"{form.ats_wins}-{form.ats_losses}-{form.ats_pushes}",
        "ou": f"{form.ou_overs}-{form.ou_unders}-{form.ou_pushes}",
        "su": f"{form.su_wins}-{form.su_losses}",
    }


@router.get("/week/{week}")
def get_week_predictions(week: int, season: int = Query(default=CURRENT_SEASON)):
    db = SessionLocal()
    try:
        rows = (
            db.query(ModelPrediction, BettingSystem, Game)
            .join(BettingSystem, ModelPrediction.system_id == BettingSystem.id)
            .join(Game, ModelPrediction.game_id == Game.id)
            .filter(Game.season == season, Game.week == week)
            .all()
        )

        game_ids = list({game.id for _, _, game in rows})
        venues_by_id = {v.id: v for v in db.query(Venue).filter(
            Venue.id.in_([g.venue_id for _, _, g in rows if g.venue_id])
        ).all()}
        weather_by_game = {
            w.game_id: w for w in db.query(WeatherSnapshot).filter(
                WeatherSnapshot.game_id.in_(game_ids)
            ).all()
        }

        team_ids = list({g.home_team_id for _, _, g in rows} | {g.away_team_id for _, _, g in rows})
        teams_by_id = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}

        season_records = {tid: get_season_record(tid, season, db) for tid in team_ids}
        recent_forms = {tid: get_recent_form_summary(tid, db) for tid in team_ids}

        results = []
        for pred, system, game in rows:
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
            })

        return {"season": season, "week": week, "count": len(results), "predictions": results}
    finally:
        db.close()