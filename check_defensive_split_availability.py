"""
Checks whether team_advanced_stats.raw_json actually contains
defense-side pass/rush success rate splits (mirroring the offense
splits we already extract) - the data needed to build real
offense-vs-defense MATCHUP features, instead of our current
offense-vs-offense comparisons.
"""
from app.db import SessionLocal
from app.models import Team, TeamAdvancedStat

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()
sample = db.query(TeamAdvancedStat).filter(
    TeamAdvancedStat.team_id == alabama.id, TeamAdvancedStat.year == 2023
).first()

if sample and sample.raw_json:
    defense = sample.raw_json.get("defense", {})
    print("Defense section keys:", list(defense.keys()))
    print("\nDefense passingPlays:", defense.get("passingPlays"))
    print("\nDefense rushingPlays:", defense.get("rushingPlays"))
else:
    print("No sample found")

db.close()