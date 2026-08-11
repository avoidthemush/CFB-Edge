import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Team

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
db = SessionLocal()
school_names = {t.school for t in db.query(Team).all()}

with cfbd.ApiClient(configuration) as api_client:
    teams_api = cfbd.TeamsApi(api_client)

    for year in [2021, 2023, 2024]:
        results = teams_api.get_talent(year=year)
        print(f"\nYear {year}: {len(results)} rows returned by CFBD")

        no_match = [r.team for r in results if r.team not in school_names]
        if no_match:
            print(f"  No match: {no_match}")

db.close()