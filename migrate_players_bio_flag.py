from sqlalchemy import text
from app.db import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE players ADD COLUMN IF NOT EXISTS has_complete_bio BOOLEAN DEFAULT TRUE"
        ))
        conn.commit()
    print("Migration complete: players.has_complete_bio added")