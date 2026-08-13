from app.db import SessionLocal
from app.models import Team, CoachSeason, CoachTendency, TeamAdvancedStat
from app.features.build_team_features import _extract_advanced_stat_fields

db = SessionLocal()
alabama = db.query(Team).filter(Team.school == "Alabama").first()

# What DeBoer's coach_id is, and whether a tendency profile exists for him at 2024
coach_season_2024 = db.query(CoachSeason).filter(
    CoachSeason.team_id == alabama.id, CoachSeason.year == 2024
).first()
print(f"Alabama 2024 coach_id: {coach_season_2024.coach_id if coach_season_2024 else 'NONE'}")

tendency = db.query(CoachTendency).filter(
    CoachTendency.coach_id == coach_season_2024.coach_id,
    CoachTendency.as_of_year == 2024,
).first()

if tendency:
    print(f"\nCoach tendency FOUND - seasons_used: {tendency.seasons_used}")
    print(f"  pass_rate: {tendency.pass_rate}")
    print(f"  off_success_rate: {tendency.off_success_rate}")
    print(f"  def_havoc_rate: {tendency.def_havoc_rate}")
else:
    print("\nCoach tendency NOT FOUND - blend would have silently fallen back to pure team history")

# What Alabama's raw 2023 (pre-DeBoer) numbers looked like, unblended
prior_adv = db.query(TeamAdvancedStat).filter(
    TeamAdvancedStat.team_id == alabama.id, TeamAdvancedStat.year == 2023
).first()
raw_2023 = _extract_advanced_stat_fields(prior_adv.raw_json if prior_adv else None)
print(f"\nAlabama's RAW 2023 (Saban, unblended):")
print(f"  pass_rate: {raw_2023.get('pass_rate')}")
print(f"  off_success_rate: {raw_2023.get('off_success_rate')}")
print(f"  def_havoc_rate: {raw_2023.get('def_havoc_rate')}")

db.close()