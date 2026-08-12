import os
import cfbd
from dotenv import load_dotenv
from datetime import datetime

from app.db import SessionLocal
from app.models import Coach, CoachSeason, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def sync_coaches():
    """
    One bulk call, no year parameter needed - get_coaches returns every
    coach with their FULL career season history nested inside. Historical
    range comes from the data itself, not a year loop like most other
    syncs.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    coaches_inserted = 0
    coaches_updated = 0
    seasons_inserted = 0
    seasons_updated = 0
    skipped_team = set()

    try:
        with cfbd.ApiClient(configuration) as api_client:
            coaches_api = cfbd.CoachesApi(api_client)
            coaches = coaches_api.get_coaches(min_year=HISTORICAL_START_YEAR, max_year=CURRENT_SEASON)
            tracker = ApiUsageTracker("sync_coaches")
            tracker.tick()

            for c in coaches:
                coach_id = getattr(c, "id", None)
                if coach_id is None:
                    continue

                fields = dict(
                    first_name=getattr(c, "first_name", None),
                    last_name=getattr(c, "last_name", None),
                    hire_date=_parse_date(getattr(c, "hire_date", None)),
                )

                existing = db.query(Coach).filter(Coach.id == coach_id).first()
                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    coaches_updated += 1
                else:
                    db.add(Coach(id=coach_id, **fields))
                    coaches_inserted += 1

                for s in getattr(c, "seasons", []) or []:
                    year = getattr(s, "year", None)
                    if year is None or year < HISTORICAL_START_YEAR or year > CURRENT_SEASON:
                        continue

                    team_name = getattr(s, "school", None)
                    team_id = resolve_team_id(team_name, school_to_id) if team_name else None
                    if team_name and team_id is None:
                        skipped_team.add(team_name)

                    season_fields = dict(
                        team_id=team_id,
                        games=getattr(s, "games", None),
                        wins=getattr(s, "wins", None),
                        losses=getattr(s, "losses", None),
                        ties=getattr(s, "ties", None),
                        win_percentage=getattr(s, "win_percentage", None),
                        preseason_rank=getattr(s, "preseason_rank", None),
                        postseason_rank=getattr(s, "postseason_rank", None),
                        srs=getattr(s, "srs", None),
                        sp_overall=getattr(s, "sp_overall", None),
                        sp_offense=getattr(s, "sp_offense", None),
                        sp_defense=getattr(s, "sp_defense", None),
                        raw_json=s.to_dict() if hasattr(s, "to_dict") else None,
                    )

                    existing_season = db.query(CoachSeason).filter(
                        CoachSeason.coach_id == coach_id,
                        CoachSeason.year == year,
                        CoachSeason.team_id == team_id,
                    ).first()

                    if existing_season:
                        for key, value in season_fields.items():
                            setattr(existing_season, key, value)
                        seasons_updated += 1
                    else:
                        db.add(CoachSeason(coach_id=coach_id, year=year, **season_fields))
                        seasons_inserted += 1

            db.commit()
            tracker.report()
            print(f"Coaches: inserted {coaches_inserted}, updated {coaches_updated}")
            print(f"Coach-seasons: inserted {seasons_inserted}, updated {seasons_updated}")
            if skipped_team:
                print(f"Unresolved team names: {list(skipped_team)[:10]}")

    except Exception as e:
        db.rollback()
        print(f"FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sync_coaches()