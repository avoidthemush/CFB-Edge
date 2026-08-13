from sqlalchemy import text
from app.db import engine

with engine.connect() as conn:
    conn.execute(text("DROP TABLE offensive_returning_production"))
    print("Dropped empty offensive_returning_production")

    conn.execute(text("ALTER TABLE returning_production RENAME TO offensive_returning_production"))
    print("Renamed returning_production -> offensive_returning_production")

    count = conn.execute(text("SELECT COUNT(*) FROM offensive_returning_production")).scalar()
    print(f"\nVerified: offensive_returning_production now has {count} rows")

    conn.commit()