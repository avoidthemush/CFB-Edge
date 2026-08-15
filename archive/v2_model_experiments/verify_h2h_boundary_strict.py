"""
Check 2 in the original leakage test was weak - it found a coach pair
with 0 prior meetings, which never actually exercised the exclusion
logic. This finds a coach pair with MULTIPLE real meetings and directly
verifies the current game is excluded from its own history, and that
only genuinely PRIOR meetings count.
"""
from collections import Counter
from app.db import SessionLocal
from app.models import Game
from app.features.coach_h2h import build_team_coach_map, build_h2h_index, get_h2h_record

db = SessionLocal()

team_coach_map = build_team_coach_map(db)
h2h_index = build_h2h_index(db, team_coach_map)

# Find a coach pair with the most meetings, to stress-test properly
pair_counts = Counter({k: len(v) for k, v in h2h_index.items()})
most_common_pair, meeting_count = pair_counts.most_common(1)[0]
print(f"Testing coach pair with {meeting_count} real meetings")

meetings = sorted(h2h_index[most_common_pair])
print(f"All meetings (season, week, winning_coach_id): {meetings}")

# Take the LAST meeting in the list and verify: querying "before" that
# exact game should NOT include that game itself, but SHOULD include
# every earlier one
coach_a, coach_b = tuple(most_common_pair)
last_season, last_week, _ = meetings[-1]

wins, losses, found_meetings = get_h2h_record(coach_a, coach_b, last_season, last_week, h2h_index)
expected_prior_meetings = len(meetings) - 1  # everything except the last one itself

print(f"\nQuerying h2h record AS OF the last meeting ({last_season}, week {last_week}):")
print(f"  Meetings found: {found_meetings}")
print(f"  Expected (total - the current game itself): {expected_prior_meetings}")
print(f"  {'PASS - current game correctly excluded' if found_meetings == expected_prior_meetings else 'FAIL - leakage detected'}")

db.close()