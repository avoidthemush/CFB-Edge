import os
import re
import unicodedata
import httpx
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Team, TeamSourceAlias

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

SPORT_KEY = "americanfootball_ncaaf"

# Known cases where the Odds API uses a genuinely different word than CFBD,
# not just an added mascot - these can't be solved by prefix matching and
# must be confirmed by hand. Add to this as we discover more.
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
}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("&", " and ")
    s = s.replace("'", "").replace("’", "").replace(".", "")
    s = s.replace("-", " ")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fetch_odds_api_team_names():
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
    print(f"Pulled {len(events)} upcoming events, {len(names)} unique team names. Quota remaining: {remaining}")
    return names


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


def build_crosswalk():
    db = SessionLocal()

    verified_teams = db.query(Team).filter(Team.is_verified == True).all()
    normalized_lookup = {normalize(t.school): (t.school, t.id) for t in verified_teams}

    odds_names = fetch_odds_api_team_names()

    existing_aliases = {
        row.source_name for row in
        db.query(TeamSourceAlias).filter(TeamSourceAlias.source == "odds_api").all()
    }
    new_names = odds_names - existing_aliases

    resolved = []
    unresolved = []

    for odds_name in sorted(new_names):
        if odds_name in MANUAL_OVERRIDES:
            target_school = MANUAL_OVERRIDES[odds_name]
            match = next((t for t in verified_teams if t.school == target_school), None)
            if match:
                db.add(TeamSourceAlias(
                    team_id=match.id, source="odds_api", source_name=odds_name,
                    confidence=1.0, verified=False,
                ))
                resolved.append((odds_name, match.school, "manual override"))
                continue

        result = find_prefix_match(odds_name, normalized_lookup)
        if result:
            school, team_id = result
            db.add(TeamSourceAlias(
                team_id=team_id, source="odds_api", source_name=odds_name,
                confidence=1.0, verified=False,
            ))
            resolved.append((odds_name, school, "prefix match"))
        else:
            db.add(TeamSourceAlias(
                team_id=None, source="odds_api", source_name=odds_name,
                confidence=0.0, verified=False,
            ))
            unresolved.append(odds_name)

    db.commit()
    db.close()

    print(f"\nResolved via exact prefix/override: {len(resolved)}")
    for odds_name, school, method in resolved:
        print(f"   '{odds_name}' -> '{school}' ({method})")

    print(f"\nUNRESOLVED - needs manual research ({len(unresolved)}):")
    for odds_name in unresolved:
        print(f"  !! '{odds_name}'")


if __name__ == "__main__":
    build_crosswalk()