from app.pipeline.sync_players import sync_roster_for_year
from app.pipeline.api_usage import ApiUsageTracker

tracker = ApiUsageTracker("test_roster")
sync_roster_for_year(year=2021, tracker=tracker, team_filter=["Alabama"])
tracker.report()