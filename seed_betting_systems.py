"""
One-time seed: registers the currently approved betting systems into
the betting_systems table. Re-runnable safely (checks for existing rows
by name+bet_type before inserting).
"""
from app.db import SessionLocal
from app.models import BettingSystem

SYSTEMS = [
    {
        "system_name": "General Model",
        "bet_type": "spread",
        "category": "general",
        "description": "Broad, always-on Spread prediction. No situational restrictions.",
        "rule_definition": {"min_confidence": 0.60},
        "status": "approved",
        "pooled_win_rate": 55.3,
        "p_value": 0.0383,
        "bootstrap_pct_profitable": 96.2,
        "sample_size": 949,
        "years_tested": "2022-2025",
    },
    {
        "system_name": "Mid-Season Dog",
        "bet_type": "spread",
        "category": "focused_value",
        "description": "Underdog-only, week 5+, non-neutral-site angle - SAME model as General Model, extra situational rules.",
        "rule_definition": {"min_confidence": 0.60, "min_week": 5, "underdog_only": True, "non_neutral_only": True},
        "status": "approved",
        "pooled_win_rate": 60.8,
        "p_value": 0.0017,
        "bootstrap_pct_profitable": 99.9,
        "sample_size": 316,
        "years_tested": "2022-2025",
    },
    {
        "system_name": "Pace Deviation",
        "bet_type": "total",
        "category": "market_deviation",
        "description": "Bets when the market's posted total is an outlier relative to recent games with similar combined pace. Independent Type B system - not a filtered version of another model.",
        "rule_definition": {"bucket_dimension": "combined_pace", "percentile_threshold": 0.15},
        "status": "approved",
        "pooled_win_rate": 55.0,
        "p_value": 0.0577,
        "bootstrap_pct_profitable": 95.0,
        "sample_size": 936,
        "years_tested": "2022-2025",
    },
    {
        "system_name": "Field Position Deviation",
        "bet_type": "total",
        "category": "market_deviation",
        "description": "Bets when the market's posted total is an outlier relative to recent games with similar combined offensive field-position value. Independent Type B system, parallel to Pace Deviation, not derived from it.",
        "rule_definition": {"bucket_dimension": "combined_field_position", "percentile_threshold": 0.075},
        "status": "approved",
        "pooled_win_rate": 57.3,
        "p_value": 0.0188,
        "bootstrap_pct_profitable": 98.6,
        "sample_size": 475,
        "years_tested": "2022-2025",
    },
]


def seed():
    db = SessionLocal()
    for s in SYSTEMS:
        existing = db.query(BettingSystem).filter(
            BettingSystem.system_name == s["system_name"], BettingSystem.bet_type == s["bet_type"]
        ).first()
        if existing:
            for key, value in s.items():
                setattr(existing, key, value)
            print(f"  Updated: {s['system_name']} ({s['bet_type']})")
            continue
        db.add(BettingSystem(**s))
        print(f"  Added: {s['system_name']} ({s['bet_type']})")
    db.commit()
    db.close()


if __name__ == "__main__":
    seed()