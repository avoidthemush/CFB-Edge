import os
import cfbd
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import RatingSnapshot, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def _upsert_rating(db, team_id, year, system, rating, offense, defense, raw_json, counters):
    if team_id is None:
        counters["skipped_no_team"] += 1
        return

    existing = db.query(RatingSnapshot).filter(
        RatingSnapshot.team_id == team_id,
        RatingSnapshot.year == year,
        RatingSnapshot.system == system,
        RatingSnapshot.week.is_(None),
    ).first()

    if existing:
        existing.rating = rating
        existing.offense_rating = offense
        existing.defense_rating = defense
        existing.raw_json = raw_json
        counters["updated"] += 1
    else:
        db.add(RatingSnapshot(
            team_id=team_id, year=year, week=None, system=system,
            rating=rating, offense_rating=offense, defense_rating=defense,
            raw_json=raw_json,
        ))
        counters["inserted"] += 1


def sync_ratings_for_year(year: int, tracker: ApiUsageTracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    counters = {"inserted": 0, "updated": 0, "skipped_no_team": 0}
    school_to_id = {t.school: t.id for t in db.query(Team).all()}

    try:
        with cfbd.ApiClient(configuration) as api_client:
            ratings_api = cfbd.RatingsApi(api_client)

            # SP+
            try:
                sp_results = ratings_api.get_sp(year=year)
                tracker.tick()
                for r in sp_results:
                    team_id = school_to_id.get(getattr(r, "team", None))
                    offense = getattr(getattr(r, "offense", None), "rating", None)
                    defense = getattr(getattr(r, "defense", None), "rating", None)
                    _upsert_rating(db, team_id, year, "sp+", getattr(r, "rating", None),
                                    offense, defense, r.to_dict() if hasattr(r, "to_dict") else None, counters)
            except Exception as e:
                print(f"    SP+ failed for {year}: {e}")

            # SRS
            try:
                srs_results = ratings_api.get_srs(year=year)
                tracker.tick()
                for r in srs_results:
                    team_id = school_to_id.get(getattr(r, "team", None))
                    _upsert_rating(db, team_id, year, "srs", getattr(r, "rating", None),
                                    None, None, r.to_dict() if hasattr(r, "to_dict") else None, counters)
            except Exception as e:
                print(f"    SRS failed for {year}: {e}")

            # Elo
            try:
                elo_results = ratings_api.get_elo(year=year)
                tracker.tick()
                for r in elo_results:
                    team_id = school_to_id.get(getattr(r, "team", None))
                    _upsert_rating(db, team_id, year, "elo", getattr(r, "elo", None),
                                    None, None, r.to_dict() if hasattr(r, "to_dict") else None, counters)
            except Exception as e:
                print(f"    Elo failed for {year}: {e}")

            # FPI
            try:
                fpi_results = ratings_api.get_fpi(year=year)
                tracker.tick()
                for r in fpi_results:
                    team_id = school_to_id.get(getattr(r, "team", None))
                    _upsert_rating(db, team_id, year, "fpi", getattr(r, "fpi", None),
                                    None, None, r.to_dict() if hasattr(r, "to_dict") else None, counters)
            except Exception as e:
                print(f"    FPI failed for {year}: {e}")

            db.commit()
            print(
                f"  Year {year}: inserted {counters['inserted']}, updated {counters['updated']} "
                f"(skipped {counters['skipped_no_team']} with no team match)"
            )

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_ratings(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_ratings")
    print(f"Backfilling ratings (SP+/SRS/Elo/FPI) from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_ratings_for_year(year, tracker)
    tracker.report()


def sync_current_ratings(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_ratings")
    sync_ratings_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_ratings()