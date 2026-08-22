"""
Cron entrypoint for the 5-minute odds-polling job. Wraps
sync_live_odds() with logging and error handling appropriate for
UNATTENDED execution.

REAL GAP FOUND AND FIXED (Aug 2026): this job only ever synced fresh
odds - nothing then actually re-checked qualification against them.
model_predictions was only ever populated by manually running each
model's predict_week.py in a terminal, meaning every week except
whichever one we'd last run by hand showed zero picks. Since all three
predict_week scripts were specifically optimized last night for a fast,
frequent-recheck architecture (~11-17s combined), they now run here,
right after each odds sync - qualification regenerates automatically
every 5 minutes for whatever week is currently cached
(game_feature_cache is intentionally scoped to the current week only,
so this naturally never touches far-future weeks until they become
relevant).
"""
import sys
import traceback
from datetime import datetime, timezone
from app.pipeline.sync_betting_lines import sync_live_odds
from app.models_ml.spread.predict_week import predict_upcoming_week as predict_spread
from app.models_ml.total.predict_week import predict_upcoming_week as predict_total
from app.models_ml.moneyline.predict_week import predict_upcoming_week as predict_moneyline


def run():
    start = datetime.now(timezone.utc)
    print(f"[{start.isoformat()}] Odds poll starting...")

    try:
        result = sync_live_odds()
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        print(f"[{datetime.now(timezone.utc).isoformat()}] Odds sync completed in {elapsed:.1f}s. Result: {result}")
    except Exception as e:
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        print(f"[{datetime.now(timezone.utc).isoformat()}] Odds sync FAILED after {elapsed:.1f}s: {e}")
        traceback.print_exc()
        return 1

    prediction_steps = [
        ("spread", predict_spread),
        ("total", predict_total),
        ("moneyline", predict_moneyline),
    ]

    failures = []
    for name, fn in prediction_steps:
        step_start = datetime.now(timezone.utc)
        try:
            print(f"\n--- Re-checking qualification: {name} ---")
            fn(write_to_db=True)
            elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
            print(f"--- Completed: {name} ({elapsed:.1f}s) ---")
        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
            print(f"--- FAILED: {name} after {elapsed:.1f}s: {e} ---")
            traceback.print_exc()
            failures.append(name)

    total_elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    if failures:
        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Odds poll completed with FAILURES in: "
              f"{failures} (total {total_elapsed:.1f}s)")
        return 1

    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Odds poll + full qualification recheck "
          f"completed successfully (total {total_elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(run())