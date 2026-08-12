from sqlalchemy import text
from app.db import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        # Old coaches table was never populated (no sync script existed
        # yet) - safe to drop and recreate cleanly rather than migrate.
        conn.execute(text("DROP TABLE IF EXISTS coaches"))
        conn.commit()
    print("Dropped old empty coaches table - init_db.py will recreate it with the new structure")