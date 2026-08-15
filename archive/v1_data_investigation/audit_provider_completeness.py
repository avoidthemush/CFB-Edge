from app.db import SessionLocal
from app.models import CFBDBettingLine
from sqlalchemy import func

db = SessionLocal()

providers = db.query(CFBDBettingLine.provider).distinct().all()

print(f"{'Provider':<30} {'Rows':>6} {'Spread':>7} {'SprdOpn':>8} {'Total':>6} {'TotOpn':>7} {'HomeML':>7} {'AwayML':>7}")

for (provider,) in providers:
    rows = db.query(CFBDBettingLine).filter(CFBDBettingLine.provider == provider)
    total = rows.count()

    def pct(col):
        n = rows.filter(col.isnot(None)).count()
        return f"{(n/total*100):.0f}%" if total else "0%"

    print(f"{provider:<30} {total:>6} "
          f"{pct(CFBDBettingLine.spread):>7} "
          f"{pct(CFBDBettingLine.spread_open):>8} "
          f"{pct(CFBDBettingLine.over_under):>6} "
          f"{pct(CFBDBettingLine.over_under_open):>7} "
          f"{pct(CFBDBettingLine.home_moneyline):>7} "
          f"{pct(CFBDBettingLine.away_moneyline):>7}")

db.close()