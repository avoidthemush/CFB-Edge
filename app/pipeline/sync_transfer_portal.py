import os
import cfbd
from dotenv import load_dotenv
from datetime import datetime
from enum import Enum

from app.db import SessionLocal
from app.models import TransferPortalEntry, Team
from app.pipeline.api_usage import ApiUsageTracker
from app.pipeline.team_resolver import resolve_team_id
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")


def _json_safe(obj):
    """
    Recursively converts a dict/list structure into something the JSON
    column type can actually serialize - datetimes become ISO strings,
    enums become their .value. Needed here specifically because
    TransferPortal's eligibility field is an Enum and transfer_date is a
    datetime, neither of which to_dict() fully flattens on its own.
    """
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    return obj


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def sync_transfer_portal_for_year(year: int, tracker: ApiUsageTracker):
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    school_to_id = {t.school: t.id for t in db.query(Team).all()}
    inserted = 0
    skipped_origin = 0
    skipped_dest = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            players_api = cfbd.PlayersApi(api_client)
            results = players_api.get_transfer_portal(year=year)
            tracker.tick()

            db.query(TransferPortalEntry).filter(TransferPortalEntry.year == year).delete()

            for r in results:
                first_name = getattr(r, "first_name", None)
                last_name = getattr(r, "last_name", None)
                full_name = f"{first_name or ''} {last_name or ''}".strip() or None

                origin_name = getattr(r, "origin", None)
                dest_name = getattr(r, "destination", None)

                origin_id = resolve_team_id(origin_name, school_to_id) if origin_name else None
                dest_id = resolve_team_id(dest_name, school_to_id) if dest_name else None

                if origin_name and origin_id is None:
                    skipped_origin += 1
                if dest_name and dest_id is None:
                    skipped_dest += 1

                eligibility_raw = getattr(r, "eligibility", None)
                eligibility_value = eligibility_raw.value if isinstance(eligibility_raw, Enum) else eligibility_raw

                raw = r.to_dict() if hasattr(r, "to_dict") else None
                raw = _json_safe(raw)

                db.add(TransferPortalEntry(
                    player_name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                    position=getattr(r, "position", None),
                    origin_team_id=origin_id,
                    destination_team_id=dest_id,
                    year=year,
                    transfer_date=_parse_date(getattr(r, "transfer_date", None)),
                    rating=getattr(r, "rating", None),
                    stars=getattr(r, "stars", None),
                    eligibility=eligibility_value,
                    raw_json=raw,
                ))
                inserted += 1

            db.commit()
            print(f"  Year {year}: inserted {inserted} "
                  f"(unresolved origin: {skipped_origin}, unresolved destination: {skipped_dest})")

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_transfer_portal(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_transfer_portal")
    print(f"Backfilling transfer portal from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_transfer_portal_for_year(year, tracker)
    tracker.report()


def sync_current_transfer_portal(year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("sync_current_transfer_portal")
    sync_transfer_portal_for_year(year, tracker)
    tracker.report()


if __name__ == "__main__":
    backfill_transfer_portal()