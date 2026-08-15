from app.db import SessionLocal
from app.models import PlayerSeasonStat, Player, Team

db = SessionLocal()

print("=== Row counts by year ===")
for year in range(2021, 2027):
    n = db.query(PlayerSeasonStat).filter(PlayerSeasonStat.year == year).count()
    print(f"  {year}: {n}")

print("\n=== Field completeness (2025) ===")
total = db.query(PlayerSeasonStat).filter(PlayerSeasonStat.year == 2025).count()
fields = [
    "tackles_total", "tackles_solo", "tackles_for_loss", "sacks", "passes_defended",
    "qb_hurries", "interceptions", "fumbles_recovered", "defensive_tds",
    "passing_yards", "rushing_yards", "receiving_yards",
]
for field in fields:
    col = getattr(PlayerSeasonStat, field)
    n = db.query(PlayerSeasonStat).filter(PlayerSeasonStat.year == 2025, col.isnot(None)).count()
    print(f"  {field}: {n}/{total} ({n/total*100:.1f}%)")

print("\n=== Orphan check: team_id references ===")
valid_team_ids = {t.id for t in db.query(Team.id).all()}
orphans = db.query(PlayerSeasonStat).filter(
    PlayerSeasonStat.team_id.isnot(None),
    ~PlayerSeasonStat.team_id.in_(valid_team_ids)
).count()
print(f"  Orphaned team_id: {orphans}")

print("\n=== Orphan check: player_id references ===")
valid_player_ids = {p.id for p in db.query(Player.id).all()}
orphan_players = db.query(PlayerSeasonStat).filter(
    ~PlayerSeasonStat.player_id.in_(valid_player_ids)
).count()
print(f"  Orphaned player_id: {orphan_players}")

print("\n=== Sample: a real defensive standout, 2025 ===")
sample = db.query(PlayerSeasonStat).filter(
    PlayerSeasonStat.year == 2025,
    PlayerSeasonStat.sacks.isnot(None),
    PlayerSeasonStat.sacks > 5,
).first()
if sample:
    player = db.query(Player).filter(Player.id == sample.player_id).first()
    print(f"  {player.name}: tackles={sample.tackles_total}, sacks={sample.sacks}, "
          f"TFL={sample.tackles_for_loss}, PD={sample.passes_defended}")

db.close()