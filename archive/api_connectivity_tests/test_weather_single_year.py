from app.pipeline.sync_weather import sync_historical_weather_for_year
from app.pipeline.api_usage import ApiUsageTracker

tracker = ApiUsageTracker("test_weather")
sync_historical_weather_for_year(2025, tracker)
tracker.report()