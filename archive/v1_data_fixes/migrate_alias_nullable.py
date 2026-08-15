from sqlalchemy import text
from app.db import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE team_source_aliases ALTER COLUMN team_id DROP NOT NULL"
        ))
        conn.commit()
    print("Migration complete: team_source_aliases.team_id is now nullable")