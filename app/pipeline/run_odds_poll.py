"""
Cron entrypoint for the 5-minute odds-polling job.

REAL ARCHITECTURE BUG FOUND AND FIXED (Aug 22, 2026): the original fix
attempted to have the DAILY-SYNC cron job generate
spread_production_model.joblib and total_production_systems.json, then
have THIS job read them. This never could have worked - each Railway
cron service runs in its own ISOLATED container with its own separate
filesystem; they share no disk space at all without an explicitly
configured shared Volume (which doesn't exist here). Files written by
one service are invisible to another.

CORRECT FIX: since training only takes ~0.3s + ~0.2s (confirmed via
real local timing), this job now generates BOTH artifacts itself,
fresh, at the start of every single run - no cross-service dependency,
no shared filesystem needed. Negligible added cost to a job that
already completes in ~1-2s.
"""
import sys
import traceback
from datetime import datetime, timezone
from app.pipeline.sync_betting_lines import sync_live_odds
from app.models_ml.spread.train_production_spread import train_production_model as train_spread_model
from app.models_ml.total.train_production_total import train_production_total
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

    print("\n--- Ensuring production model artifacts exist in THIS container ---")
    try:
        train_spread_model()
        train_production_total()
        print("--- Model artifacts ready ---")
    except Exception as e:
        print(f"--- FAILED to generate model artifacts: {e} ---")
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