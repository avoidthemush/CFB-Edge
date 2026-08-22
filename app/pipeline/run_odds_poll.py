"""
Cron entrypoint for the 5-minute odds-polling job.

REAL FIX (Aug 22, 2026): two prior attempts tried to have this job (or
a separate daily job) REGENERATE spread_production_model.joblib and
total_production_systems.json inside Railway - both wrong. The correct,
standard approach for deploying a trained model: train LOCALLY (where
the full historical training CSV exists), then COMMIT the small,
final artifact files to git. Railway reads them like any other code -
no training ever happens in production. This job's only job is:
sync fresh odds, then re-check qualification against the already-
committed artifacts.
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