"""
One-time full database backup - dumps every table to CSV in a local
backups/ folder, timestamped. Not a substitute for Railway's real backup
system, but a free, no-plan-required safety net for the v1 checkpoint
specifically. Run again anytime you want a new snapshot.
"""
import os
import csv
from datetime import datetime

from app.db import engine
from sqlalchemy import inspect, text

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f"backups/v1_snapshot_{timestamp}"
os.makedirs(backup_dir, exist_ok=True)

inspector = inspect(engine)
table_names = inspector.get_table_names()

print(f"Backing up {len(table_names)} tables to {backup_dir}/\n")

with engine.connect() as conn:
    for table in sorted(table_names):
        result = conn.execute(text(f"SELECT * FROM {table}"))
        rows = result.fetchall()
        columns = result.keys()

        filepath = os.path.join(backup_dir, f"{table}.csv")
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        print(f"  {table}: {len(rows)} rows")

print(f"\nBackup complete: {backup_dir}/")