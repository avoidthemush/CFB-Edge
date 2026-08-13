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
    recruiting_api = cfbd.RecruitingApi(api_client)

    for year in [2025, 2026]:
        results = recruiting_api.get_team_recruiting_rankings(year=year)
        no_match = [r.team for r in results if r.team not in school_names]
        print(f"Year {year} no match: {no_match}")

db.close()