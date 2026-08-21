"""
Cron entrypoint for the DAILY 2am UTC job: syncs current-season weekly
stats, advanced stats, rankings, and ratings, THEN refreshes the game
feature cache for the current week - chained in one script rather than
two independently-scheduled jobs, since Railway cron doesn't support
job dependencies. This guarantees the cache refresh always runs AFTER
fresh stats are in, never before.

Runs daily (not weekly) since CFB games happen on more days than just
weekends (Tue/Wed MAC games are real), and daily re-sync is more
resilient to CFBD's own data-finalization lag than a fixed weekly day.//
2am UTC is chosen to be safely after even the latest West Coast games
(kickoff ~10:30pm Pacific can finish past 1am Eastern) have wrapped and
had time for CFBD to post final stats.
"""
import sys
import traceback
from datetime import datetime
from app.config import CURRENT_SEASON
from app.pipeline.sync_weekly_stats import sync_current_weekly_stats
from app.pipeline.sync_advanced_stats import sync_current_advanced_stats
from app.pipeline.sync_rankings import sync_current_rankings
from app.pipeline.sync_ratings import sync_current_ratings
from app.pipeline.refresh_game_feature_cache import refresh_cache


def run():
    start = datetime.utcnow()
    print(f"[{start.isoformat()}] Daily sync starting for season {CURRENT_SEASON}...")

    steps = [
        ("weekly team stats", lambda: sync_current_weekly_stats(CURRENT_SEASON)),
        ("advanced stats", lambda: sync_current_advanced_stats(CURRENT_SEASON)),
        ("rankings", lambda: sync_current_rankings(CURRENT_SEASON)),
        ("ratings", lambda: sync_current_ratings(CURRENT_SEASON)),
        ("game feature cache refresh", lambda: refresh_cache(CURRENT_SEASON)),
    ]

    failures = []
    for step_name, step_fn in steps:
        step_start = datetime.utcnow()
        try:
            print(f"\n--- Running: {step_name} ---")
            step_fn()
            elapsed = (datetime.utcnow() - step_start).total_seconds()
            print(f"--- Completed: {step_name} ({elapsed:.1f}s) ---")
        except Exception as e:
            elapsed = (datetime.utcnow() - step_start).total_seconds()
            print(f"--- FAILED: {step_name} after {elapsed:.1f}s: {e} ---")
            traceback.print_exc()
            failures.append(step_name)
            # Continue to remaining steps rather than aborting entirely -
            # e.g. if rankings sync fails, stats/ratings/cache-refresh
            # should still attempt to run rather than all being skipped.

    total_elapsed = (datetime.utcnow() - start).total_seconds()
    if failures:
        print(f"\n[{datetime.utcnow().isoformat()}] Daily sync completed with FAILURES in: "
              f"{failures} (total {total_elapsed:.1f}s)")
        return 1

    print(f"\n[{datetime.utcnow().isoformat()}] Daily sync completed successfully "
          f"(total {total_elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(run())