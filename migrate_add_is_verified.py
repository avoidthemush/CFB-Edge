from sqlalchemy import text
from app.db import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE teams ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT TRUE"
        ))
        conn.commit()
    print("Migration complete: teams.is_verified added")