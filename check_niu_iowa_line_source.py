from app.db import SessionLocal
from app.models import Game, CFBDBettingLine, OddsSnapshot

db = SessionLocal()

game = db.query(Game).filter(
    Game.season == 2026, Game.week == 1,
    Game.home_team_name.ilike("%Iowa%"), Game.away_team_name.ilike("%Northern Illinois%"),
).first()

if game is None:
    print("Game not found - check team name matching")
else:
    print(f"Game: {game.away_team_name} @ {game.home_team_name}, id={game.id}\n")

    cfbd_lines = db.query(CFBDBettingLine).filter(CFBDBettingLine.game_id == game.id).all()
    print(f"=== CFBD betting lines ({len(cfbd_lines)} rows) ===")
    for line in cfbd_lines:
        print(f"  provider={line.provider}, spread={line.spread}, spread_open={line.spread_open}, "
              f"total={line.over_under}, total_open={line.over_under_open}")

    odds_rows = db.query(OddsSnapshot).filter(OddsSnapshot.game_id == game.id).all()
    print(f"\n=== Our own odds_snapshots (live Odds API polls) ({len(odds_rows)} rows) ===")
    for row in odds_rows:
        print(f"  book={row.sportsbook}, total={row.total}, spread_home={row.spread_home}, pulled_at={row.pulled_at}")

db.close()