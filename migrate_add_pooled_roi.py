"""
One-time migration: adds the pooled_roi column to the live betting_systems
table (init_db.py's create_all() only creates missing TABLES, not new
columns on existing ones - a real ALTER TABLE is needed here), then
backfills the one system that actually needs it: Unranked Favorite Dog,
whose raw win rate (41%) is misleading without the real ROI context.
"""
from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import BettingSystem

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE betting_systems ADD COLUMN IF NOT EXISTS pooled_roi FLOAT"
    ))
    conn.commit()
print("Column pooled_roi added (or already existed).")

db = SessionLocal()
system = db.query(BettingSystem).filter(
    BettingSystem.system_name == "Unranked Favorite Dog", BettingSystem.bet_type == "moneyline"
).first()

if system:
    system.pooled_roi = 6.3
    db.commit()
    print(f"Backfilled pooled_roi=6.3 for '{system.system_name}'")
else:
    print("WARNING: Unranked Favorite Dog not found - check seed_betting_systems.py has run")

db.close()