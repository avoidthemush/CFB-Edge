from sqlalchemy import text
from app.db import engine

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('returning_production', 'offensive_returning_production')
    """))
    tables = [row[0] for row in result]
    print(f"Tables found: {tables}")

    for t in tables:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  {t}: {count} rows")