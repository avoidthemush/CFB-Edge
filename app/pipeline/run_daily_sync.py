"""
Cron entrypoint for the DAILY 2am UTC job: syncs current-season weekly
stats, advanced stats, rankings, ratings, and upcoming-game weather
forecasts, retrains/regenerates the Spread and Total production model
artifacts, THEN refreshes the game feature cache and team recent-form
records.

REAL BUG FOUND AND FIXED (Aug 22, 2026): spread_production_model.joblib
and total_production_systems.json are both gitignored (correctly - they
are generated artifacts, not source code) but this meant Railway's
environment never actually HAD these files at all, since Railway only
ever receives what's in the git repo. This caused the 5-min odds-poll
cron job to silently fail on Spread and Total qualification checks
every single run since it was first deployed - only Moneyline (pure
rule logic, no saved model) ever actually succeeded. Fixed by having
Railway generate these artifacts itself, daily, so they always exist
fresh before the odds-poll job needs them.
"""
import sys
import traceback
from datetime import datetime, timezone
from app.config import CURRENT_SEASON
from app.pipeline.sync_weekly_stats import sync_current_weekly_stats
from app.pipeline.sync_advanced_stats import sync_current_advanced_stats
from app.pipeline.sync_rankings import sync_current_rankings
from app.pipeline.sync_ratings import sync_current_ratings
from app.pipeline.sync_weather import sync_weather_for_upcoming_games
from app.models_ml.spread.train_production_spread import train_production_model as train_spread_model
from app.models_ml.total.train_production_total import train_production_total
from app.pipeline.refresh_game_feature_cache import refresh_cache
from app.pipeline.refresh_team_recent_form import refresh_recent_form


def run():
    start = datetime.now(timezone.utc)
    print(f"[{start.isoformat()}] Daily sync starting for season {CURRENT_SEASON}...")

    steps = [
        ("weekly team stats", lambda: sync_current_weekly_stats(CURRENT_SEASON)),
        ("advanced stats", lambda: sync_current_advanced_stats(CURRENT_SEASON)),
        ("rankings", lambda: sync_current_rankings(CURRENT_SEASON)),
        ("ratings", lambda: sync_current_ratings(CURRENT_SEASON)),
        ("weather forecasts (upcoming games)", lambda: sync_weather_for_upcoming_games()),
        ("regenerate spread production model", lambda: train_spread_model()),
        ("regenerate total production systems", lambda: train_production_total()),
        ("game feature cache refresh", lambda: refresh_cache(CURRENT_SEASON)),
        ("team recent-form refresh", lambda: refresh_recent_form()),
    ]

    failures = []
    for step_name, step_fn in steps:
        step_start = datetime.now(timezone.utc)
        try:
            print(f"\n--- Running: {step_name} ---")
            step_fn()
            elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
            print(f"--- Completed: {step_name} ({elapsed:.1f}s) ---")
        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
            print(f"--- FAILED: {step_name} after {elapsed:.1f}s: {e} ---")
            traceback.print_exc()
            failures.append(step_name)

    total_elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    if failures:
        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Daily sync completed with FAILURES in: "
              f"{failures} (total {total_elapsed:.1f}s)")
        return 1

    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Daily sync completed successfully "
          f"(total {total_elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(run())