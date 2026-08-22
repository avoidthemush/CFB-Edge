"""
Cron entrypoint for the DAILY 2am UTC job: syncs current-season weekly
stats, advanced stats, rankings, ratings, and upcoming-game weather
forecasts, THEN refreshes the game feature cache and team recent-form
records.

NOTE (Aug 22, 2026): model artifact generation (spread_production_model,
total_production_systems) was briefly added here, then removed - it
never could have helped the separate odds-poll cron service, since
Railway services don't share a filesystem across containers. That
generation now correctly lives inside run_odds_poll.py itself, the only
place that actually needs it.
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