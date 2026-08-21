"""
Real test of kickoff-aware logic, using an actual Week 1 2026 FBS game
with genuine live-polled snapshot data (confirmed earlier: 738 rows
from real polling). Tests both the REAL kickoff time (should include
all snapshots, is_closing=False since kickoff hasn't happened) and a
FABRICATED earlier kickoff time (should exclude later snapshots and
flip is_closing=True) - directly proving the filter logic works, not
just returning "no data" from a badly-chosen test case.
"""
from datetime import timedelta
from app.db import SessionLocal
from app.models import Game, Team, OddsSnapshot
from app.features.get_game_line import get_live_book_lines

db = SessionLocal()

fbs_team_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}

# Find a real Week 1 2026 FBS game with actual polled snapshot data
candidate = db.query(Game).join(
    OddsSnapshot, OddsSnapshot.game_id == Game.id
).filter(
    Game.season == 2026, Game.week == 1,
    Game.home_team_id.in_(fbs_team_ids), Game.away_team_id.in_(fbs_team_ids),
).first()

if candidate is None:
    print("No FBS Week 1 game with snapshot data found - odds poll may need to run again first")
else:
    snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id == candidate.id, OddsSnapshot.sportsbook == "draftkings"
    ).order_by(OddsSnapshot.pulled_at).all()

    print(f"=== {candidate.away_team_name} @ {candidate.home_team_name} ===")
    print(f"Real kickoff: {candidate.start_date}")
    print(f"Total draftkings snapshots on file: {len(snapshots)}")
    for s in snapshots:
        print(f"  pulled_at={s.pulled_at}, spread={s.spread_home}")

    print(f"\n--- Test 1: using REAL kickoff time (should include ALL snapshots, is_closing=False) ---")
    lines = get_live_book_lines(candidate.id, db, kickoff_time=candidate.start_date)
    if "draftkings" in lines:
        line = lines["draftkings"]
        print(f"  spread={line.spread}, spread_open={line.spread_open}, is_closing={line.is_closing}")

    if len(snapshots) > 0:
        fabricated_kickoff = snapshots[0].pulled_at + timedelta(seconds=1)
        print(f"\n--- Test 2: FABRICATED kickoff time ({fabricated_kickoff}, "
              f"right after the FIRST snapshot) ---")
        lines2 = get_live_book_lines(candidate.id, db, kickoff_time=fabricated_kickoff)
        if "draftkings" in lines2:
            line2 = lines2["draftkings"]
            print(f"  spread={line2.spread}, spread_open={line2.spread_open}, is_closing={line2.is_closing}")
            print(f"  (Expected: spread should equal spread_open, since only the first "
                  f"snapshot counts as 'pre-kickoff' now; is_closing should be True)")
        else:
            print("  No usable line - means ALL snapshots got excluded (only correct if there was only 1 snapshot total)")

db.close()