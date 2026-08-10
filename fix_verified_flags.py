import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Team

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

YEARS_TO_CHECK = range(2021, 2027)  # 2021-2026 inclusive


def fix_verified_flags():
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    known_cfbd_ids = set()

    try:
        with cfbd.ApiClient(configuration) as api_client:
            api_instance = cfbd.TeamsApi(api_client)
            for year in YEARS_TO_CHECK:
                teams = api_instance.get_teams(year=year)
                for t in teams:
                    known_cfbd_ids.add(t.id)
                print(f"  Year {year}: {len(teams)} teams from CFBD (running total unique: {len(known_cfbd_ids)})")

        all_teams = db.query(Team).all()
        verified_count = 0
        stub_count = 0

        for team in all_teams:
            if team.id in known_cfbd_ids:
                team.is_verified = True
                verified_count += 1
            else:
                team.is_verified = False
                stub_count += 1

        db.commit()
        print(f"\nFixed: {verified_count} verified, {stub_count} stubs")

    except Exception as e:
        db.rollback()
        print(f"FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_verified_flags()