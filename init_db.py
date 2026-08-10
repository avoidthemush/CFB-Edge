from app.db import engine, Base
from app import models  # noqa: F401  (import so models register with Base)

if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table in Base.metadata.tables:
        print(f"  - {table}")
