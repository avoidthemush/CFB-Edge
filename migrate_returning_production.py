from sqlalchemy import text
from app.db import engine

NEW_COLUMNS = [
    "total_ppa FLOAT",
    "total_passing_ppa FLOAT",
    "total_receiving_ppa FLOAT",
    "total_rushing_ppa FLOAT",
    "percent_ppa FLOAT",
    "percent_passing_ppa FLOAT",
    "percent_receiving_ppa FLOAT",
    "percent_rushing_ppa FLOAT",
    "usage FLOAT",
    "passing_usage FLOAT",
    "receiving_usage FLOAT",
    "rushing_usage FLOAT",
]

OLD_COLUMNS_TO_DROP = ["overall_pct", "offense_pct", "defense_pct"]

if __name__ == "__main__":
    with engine.connect() as conn:
        for col_def in NEW_COLUMNS:
            col_name = col_def.split()[0]
            conn.execute(text(f"ALTER TABLE returning_production ADD COLUMN IF NOT EXISTS {col_def}"))
            print(f"Added column: {col_name}")

        for col_name in OLD_COLUMNS_TO_DROP:
            conn.execute(text(f"ALTER TABLE returning_production DROP COLUMN IF EXISTS {col_name}"))
            print(f"Dropped column: {col_name}")

        conn.commit()
    print("\nMigration complete")