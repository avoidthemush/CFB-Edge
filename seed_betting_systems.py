"""
One-time seed: registers the currently approved betting systems into
the betting_systems table, so predict_week.py can reference them by ID
instead of hardcoding names/rules in Python. Re-runnable safely
(checks for existing rows by name+bet_type before inserting).
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
        "description": "Underdog-only, week 5+, non-neutral-site angle on top of General Model.",
        "rule_definition": {"min_confidence": 0.60, "min_week": 5, "underdog_only": True, "non_neutral_only": True},
        "status": "approved",
        "pooled_win_rate": 60.8,
        "p_value": 0.0017,
        "bootstrap_pct_profitable": 99.9,
        "sample_size": 316,
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
            print(f"  Already exists: {s['system_name']} ({s['bet_type']})")
            continue
        db.add(BettingSystem(**s))
        print(f"  Added: {s['system_name']} ({s['bet_type']})")
    db.commit()
    db.close()


if __name__ == "__main__":
    seed()