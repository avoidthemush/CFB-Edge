from sqlalchemy import text
from app.db import engine

NEW_COLUMNS = [
    "first_name VARCHAR",
    "last_name VARCHAR",
    "transfer_date TIMESTAMP",
    "stars INTEGER",
    "eligibility VARCHAR",
]

if __name__ == "__main__":
    with engine.connect() as conn:
        for col_def in NEW_COLUMNS:
            col_name = col_def.split()[0]
            conn.execute(text(f"ALTER TABLE transfer_portal_entries ADD COLUMN IF NOT EXISTS {col_def}"))
            print(f"Added column: {col_name}")
        conn.commit()
    print("Migration complete")