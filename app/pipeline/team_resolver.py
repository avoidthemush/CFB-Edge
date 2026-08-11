"""
Shared team-name resolution for CFBD's own endpoints. CFBD is not fully
internally consistent - some endpoints (Recruiting, seen so far) spell a
team's name differently than the canonical Teams endpoint. This is a
DIFFERENT problem than the Odds API crosswalk (external source, different
provider naming conventions) - this is CFBD disagreeing with itself.

Add to CFBD_NAME_ALIASES whenever a new mismatch is found via a skipped
row. Genuinely different schools (e.g. Jacksonville University vs
Jacksonville State) should NOT go here - only confirmed same-school
spelling variants.
"""

CFBD_NAME_ALIASES = {
    "Saint Francis (PA)": "Saint Francis",
    "Southeastern Louisiana": "SE Louisiana",
    "Albany": "UAlbany",
    "UTRGV": "UT Rio Grande Valley",
}


def resolve_team_id(name: str, school_to_id: dict):
    """Returns team_id or None. Tries exact match first, then known aliases."""
    if name in school_to_id:
        return school_to_id[name]
    if name in CFBD_NAME_ALIASES:
        return school_to_id.get(CFBD_NAME_ALIASES[name])
    return None