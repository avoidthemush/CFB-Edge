from app.pipeline.sync_weekly_stats import sync_weekly_team_stats_for_year, sync_weekly_advanced_stats_for_year, sync_weekly_elo_for_year
from app.pipeline.api_usage import ApiUsageTracker

tracker = ApiUsageTracker("test_weekly")
print("--- Team stats ---")
sync_weekly_team_stats_for_year(2025, tracker)
print("--- Advanced stats ---")
sync_weekly_advanced_stats_for_year(2025, tracker)
print("--- Elo ---")
sync_weekly_elo_for_year(2025, tracker)
tracker.report()