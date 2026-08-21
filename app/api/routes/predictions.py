"""
Read-only endpoints for retrieving this week's qualifying picks across
all three models, joined with system metadata and game info.
"""
from fastapi import APIRouter, Query
from app.db import SessionLocal
from app.models import ModelPrediction, BettingSystem, Game
from app.config import CURRENT_SEASON

router = APIRouter()


@router.get("/week/{week}")
def get_week_predictions(week: int, season: int = Query(default=CURRENT_SEASON)):
    """
    Returns every qualifying prediction for the given week, across all
    three bet types, with system metadata and game context attached.
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(ModelPrediction, BettingSystem, Game)
            .join(BettingSystem, ModelPrediction.system_id == BettingSystem.id)
            .join(Game, ModelPrediction.game_id == Game.id)
            .filter(Game.season == season, Game.week == week)
            .all()
        )

        results = []
        for pred, system, game in rows:
            results.append({
                "matchup": f"{game.away_team_name} @ {game.home_team_name}",
                "kickoff": game.start_date.isoformat() if game.start_date else None,
                "bet_type": pred.bet_type,
                "system_name": system.system_name,
                "system_category": system.category,
                "book": pred.model_version.split(":")[-1] if ":" in (pred.model_version or "") else None,
                "bet_on_home": pred.bet_on_home,
                "predicted_value": pred.predicted_value,
                "confidence": pred.confidence,
                "market_spread_open": pred.market_spread_open,
                "market_spread_current": pred.market_spread_current,
                "predicted_at": pred.predicted_at.isoformat() if pred.predicted_at else None,
                "system_historical_win_rate": system.pooled_win_rate,
                "system_historical_bootstrap": system.bootstrap_pct_profitable,
            })

        return {"season": season, "week": week, "count": len(results), "predictions": results}
    finally:
        db.close()