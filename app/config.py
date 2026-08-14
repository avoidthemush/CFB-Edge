"""
Central place for values that change once a year, or that define the
project's historical scope. Update CURRENT_SEASON here each offseason.

Historical boundaries (verified via check_full_historical_scope.py and
check_player_data_historical.py, not assumed):
- 2013: games, betting lines, ratings, advanced stats, team season
  stats, weekly point-in-time stats, recruiting, rankings, coaches,
  weather all have real data.
- 2015: team talent, roster/player season stats/player usage,
  offensive returning production all start here (NOT bound by the
  transfer portal - that was a wrong assumption, corrected Aug 2026).
- 2019: team ATS specifically starts here - genuinely unavailable
  before this, not a choice.
- 2021: transfer portal entries only - genuinely didn't exist before
  this (the one real transfer-portal-era limitation; everything else
  originally grouped with it was wrong to group).

Project-wide floor set at 2015 (not 2013) - simpler to reason about,
covers nearly everything except ATS (2019) and transfer portal (2021),
which stay as documented, accepted gaps rather than fake-filled.
"""

CURRENT_SEASON = 2026
HISTORICAL_START_YEAR = 2015  # project-wide floor
ATS_START_YEAR = 2019  # real CFBD limitation, not a choice
TRANSFER_PORTAL_START_YEAR = 2021  # real CFBD limitation, not a choice