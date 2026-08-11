import os
import re
import unicodedata
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Team, TeamSourceAlias

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

SPORT_KEY = "americanfootball_ncaaf"

# One snapshot per week across every season 2021-2025 (games roll off the
# live feed once played, so weekly sampling is needed to see every week's
# matchups). Uses the historical /events endpoint (1 credit/call) rather
# than /odds (10 credits/call) since we only need team names, not prices.
# Windows end Jan 20 to capture each season's CFP National Championship.
SEASON_WINDOWS = [
    (datetime(2021, 8, 23), datetime(2022, 1, 20)),
    (datetime(2022, 8, 23), datetime(2023, 1, 20)),
    (datetime(2023, 8, 23), datetime(2024, 1, 20)),
    (datetime(2024, 8, 23), datetime(2025, 1, 20)),
    (datetime(2025, 8, 23), datetime(2026, 1, 20)),
]


def generate_all_weekly_dates(windows):
    dates = []
    for start, end in windows:
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%dT12:00:00Z"))
            current += timedelta(days=7)
    return dates


# Known cases where the Odds API uses a genuinely different word/spelling
# than CFBD, not just an added mascot - these can't be solved by prefix
# matching and must be confirmed by hand. Add to this as we discover more.
MANUAL_OVERRIDES = {
    "Citadel Bulldogs": "The Citadel",
    "UMass Minutemen": "Massachusetts",
    "Youngstown St Penguins": "Youngstown State",
    "Southern Mississippi Golden Eagles": "Southern Miss",
    "Albany": "UAlbany",
    "LIU Sharks": "Long Island University",
    "Southeastern Louisiana Lions": "SE Louisiana",
    "Appalachian State Mountaineers": "App State",
    "Houston Baptist Huskies": "Houston Christian",
    "Texas A&M-Commerce Lions": "East Texas A&M",
    "St. Francis (PA) Red Flash": "Saint Francis",
}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("&", " and ")
    s = s.replace("'", "").replace("’", "").replace(".", "")
    s = s.replace("-", " ")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_current_team_names():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/events"
    resp = httpx.get(url, params={"apiKey": ODDS_API_KEY}, timeout=15)
    resp.raise_for_status()
    events = resp.json()

    names = set()
    for e in events:
        if e.get("home_team"):
            names.add(e["home_team"])
        if e.get("away_team"):
            names.add(e["away_team"])

    remaining = resp.headers.get("x-requests-remaining")
    print(f"[current /events] {len(events)} events, {len(names)} unique names. Quota remaining: {remaining}")
    return names


def fetch_historical_team_names(dates):
    url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT_KEY}/events"
    all_names = set()

    for date in dates:
        resp = httpx.get(url, params={"apiKey": ODDS_API_KEY, "date": date}, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        events = payload.get("data", [])

        snapshot_names = set()
        for e in events:
            if e.get("home_team"):
                snapshot_names.add(e["home_team"])
            if e.get("away_team"):
                snapshot_names.add(e["away_team"])

        all_names |= snapshot_names
        cost = resp.headers.get("x-requests-last")
        remaining = resp.headers.get("x-requests-remaining")
        print(f"[historical {date}] {len(events)} events, {len(snapshot_names)} names "
              f"(cost: {cost}, remaining: {remaining})")

    return all_names


def find_prefix_match(odds_name: str, normalized_lookup: dict):
    """
    Odds API names follow the pattern '{exact school name} {mascot}'.
    Try the longest possible leading word-span first - this naturally
    distinguishes 'Kansas State' from 'Kansas', 'Michigan State' from
    'Michigan', etc., since we always prefer the longest exact match.
    """
    norm = normalize(odds_name)
    words = norm.split(" ")

    for k in range(len(words), 0, -1):
        candidate = " ".join(words[:k])
        if candidate in normalized_lookup:
            return normalized_lookup[candidate]
    return None


def build_crosswalk(include_historical: bool = True):
    """
    Bootstrap - not a per-season heavy task. Every match gets written as
    unverified regardless of confidence; a human confirms each one once.
    Reruns only surface genuinely new names, since already-mapped names
    are skipped.
    """
    db = SessionLocal()

    verified_teams = db.query(Team).filter(Team.is_verified == True).all()
    normalized_lookup = {normalize(t.school): (t.school, t.id) for t in verified_teams}

    odds_names = fetch_current_team_names()
    if include_historical:
        weekly_dates = generate_all_weekly_dates(SEASON_WINDOWS)
        print(f"\nSampling {len(weekly_dates)} weekly snapshots across 2021-2025 seasons...")
        odds_names |= fetch_historical_team_names(weekly_dates)

    print(f"\nTotal unique team names across all sources: {len(odds_names)}")

    existing_aliases = {
        row.source_name for row in
        db.query(TeamSourceAlias).filter(TeamSourceAlias.source == "odds_api").all()
    }
    new_names = odds_names - existing_aliases
    print(f"Already mapped (skipped): {len(odds_names) - len(new_names)}")
    print(f"New names to resolve: {len(new_names)}")

    if not new_names:
        print("\nNothing new - crosswalk is already complete.")
        db.close()
        return

    rows = []
    for odds_name in sorted(new_names):
        if odds_name in MANUAL_OVERRIDES:
            target_school = MANUAL_OVERRIDES[odds_name]
            match = next((t for t in verified_teams if t.school == target_school), None)
            if match:
                db.add(TeamSourceAlias(
                    team_id=match.id, source="odds_api", source_name=odds_name,
                    confidence=1.0, verified=False,
                ))
                rows.append((odds_name, match.school, "manual override"))
                continue

        result = find_prefix_match(odds_name, normalized_lookup)
        if result:
            school, team_id = result
            db.add(TeamSourceAlias(
                team_id=team_id, source="odds_api", source_name=odds_name,
                confidence=1.0, verified=False,
            ))
            rows.append((odds_name, school, "prefix match"))
        else:
            db.add(TeamSourceAlias(
                team_id=None, source="odds_api", source_name=odds_name,
                confidence=0.0, verified=False,
            ))
            rows.append((odds_name, None, "UNRESOLVED"))

    db.commit()
    db.close()

    print(f"\n{len(rows)} new mappings written, all unverified:\n")
    for odds_name, matched_school, method in rows:
        flag = "!!" if method == "UNRESOLVED" else "  "
        print(f"{flag} '{odds_name}' -> '{matched_school}' ({method})")


if __name__ == "__main__":
    build_crosswalk()