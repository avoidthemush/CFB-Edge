"""
Cron entrypoint for the 5-minute odds-polling job. Wraps
sync_live_odds() with logging and error handling appropriate for
UNATTENDED execution - no human watching this run, so it needs to log
enough to debug after the fact (Railway captures stdout/stderr as logs
automatically, no custom logging table needed for this).

A single failed run is not treated as fatal - it just logs the error
and exits; the next cron trigger (5 min later) will simply try again.
This is intentional: retry-via-next-scheduled-run is simpler and just
as effective as building custom retry logic for a job this frequent.
"""
import sys
import traceback
from datetime import datetime
from app.pipeline.sync_betting_lines import sync_live_odds


def run():
    start = datetime.utcnow()
    print(f"[{start.isoformat()}] Odds poll starting...")

    try:
        result = sync_live_odds()
        elapsed = (datetime.utcnow() - start).total_seconds()
        print(f"[{datetime.utcnow().isoformat()}] Odds poll completed in {elapsed:.1f}s. Result: {result}")
        return 0

    except Exception as e:
        elapsed = (datetime.utcnow() - start).total_seconds()
        print(f"[{datetime.utcnow().isoformat()}] Odds poll FAILED after {elapsed:.1f}s: {e}")
        traceback.print_exc()
        # Non-fatal: next cron trigger will retry in 5 min. Exit code 1
        # so Railway's own run-history correctly shows this as a failure.
        return 1


if __name__ == "__main__":
    sys.exit(run())