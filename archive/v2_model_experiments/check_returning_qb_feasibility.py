from app.db import SessionLocal
from app.models import Team, PlayerSeasonStat, Player

db = SessionLocal()

alabama = db.query(Team).filter(Team.school == "Alabama").first()

# Find 2023's QB1 by passing attempts
qb1_2023 = db.query(PlayerSeasonStat).filter(
    PlayerSeasonStat.team_id == alabama.id,
    PlayerSeasonStat.year == 2023,
    PlayerSeasonStat.position == "QB",
).order_by(PlayerSeasonStat.passing_attempts.desc()).first()

if qb1_2023:
    player = db.query(Player).filter(Player.id == qb1_2023.player_id).first()
    print(f"2023 QB1 (by attempts): {player.name if player else qb1_2023.player_id}, "
          f"{qb1_2023.passing_attempts} attempts")

    # Did that same player_id have passing stats for Alabama again in 2024?
    still_here_2024 = db.query(PlayerSeasonStat).filter(
        PlayerSeasonStat.player_id == qb1_2023.player_id,
        PlayerSeasonStat.team_id == alabama.id,
        PlayerSeasonStat.year == 2024,
    ).first()
    print(f"Same player has 2024 stats at Alabama: {still_here_2024 is not None}")
else:
    print("No QB found for Alabama 2023 - checking position value format")
    sample = db.query(PlayerSeasonStat).filter(
        PlayerSeasonStat.team_id == alabama.id, PlayerSeasonStat.year == 2023
    ).filter(PlayerSeasonStat.position.isnot(None)).limit(10).all()
    for s in sample:
        print(f"  position value found: '{s.position}'")

db.close()