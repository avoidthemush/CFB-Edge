from app.db import SessionLocal
from app.models import CFBDBettingLine, Game
from sqlalchemy import func

db = SessionLocal()

total_lines = db.query(CFBDBettingLine).count()
print(f"Total line rows: {total_lines}")

games_with_lines = db.query(func.count(func.distinct(CFBDBettingLine.game_id))).scalar()
total_games = db.query(Game).count()
print(f"Games with at least one line: {games_with_lines} / {total_games} total games")

print("\nProviders and row counts:")
providers = db.query(
    CFBDBettingLine.provider, func.count(CFBDBettingLine.id)
).group_by(CFBDBettingLine.provider).order_by(func.count(CFBDBettingLine.id).desc()).all()
for provider, count in providers:
    print(f"  {provider}: {count}")

print("\nField completeness (out of total line rows):")
fields = {
    "spread": CFBDBettingLine.spread,
    "spread_open": CFBDBettingLine.spread_open,
    "over_under": CFBDBettingLine.over_under,
    "over_under_open": CFBDBettingLine.over_under_open,
    "home_moneyline": CFBDBettingLine.home_moneyline,
    "away_moneyline": CFBDBettingLine.away_moneyline,
}
for name, col in fields.items():
    populated = db.query(CFBDBettingLine).filter(col.isnot(None)).count()
    pct = (populated / total_lines * 100) if total_lines else 0
    print(f"  {name}: {populated}/{total_lines} ({pct:.1f}%)")

print("\nSample row:")
sample = db.query(CFBDBettingLine).filter(CFBDBettingLine.spread_open.isnot(None)).first()
if sample:
    g = db.query(Game).filter(Game.id == sample.game_id).first()
    print(f"  {g.away_team_name} @ {g.home_team_name} ({g.season})")
    print(f"  Provider: {sample.provider}")
    print(f"  Spread: {sample.spread_open} -> {sample.spread}")
    print(f"  Total: {sample.over_under_open} -> {sample.over_under}")
    print(f"  ML: home {sample.home_moneyline}, away {sample.away_moneyline}")

db.close()