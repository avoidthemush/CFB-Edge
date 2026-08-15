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
    ratings_api = cfbd.RatingsApi(api_client)
    sp_results = ratings_api.get_sp(year=2025)
    for r in sp_results:
        team_name = getattr(r, "team", None)
        if team_name not in school_names:
            print(f"No match: '{team_name}'")

db.close()