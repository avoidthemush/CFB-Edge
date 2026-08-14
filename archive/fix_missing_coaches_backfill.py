"""
backfill_to_2015.py missed calling sync_coaches() entirely - genuine
oversight, not a CFBD limitation. sync_coaches() already reads its year
range from app.config.HISTORICAL_START_YEAR (now 2015), so calling it
now retroactively picks up 2015-2020 coaching data in one call. Must
run BEFORE recomputing coach tendencies again.
"""
from app.pipeline.sync_coaches import sync_coaches
from app.pipeline.calc_coach_tendencies import calc_coach_tendencies

print("=== Re-running coaches sync (was missed in original backfill stages) ===")
sync_coaches()

print("\n=== Re-running coach tendencies with corrected data ===")
calc_coach_tendencies()