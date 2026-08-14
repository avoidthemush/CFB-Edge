"""
Full inventory: checks actual data availability at CFBD's source for
EVERY table we've built, across a spread of years back to 2013. Confirms
which sources genuinely support extending to 2013, and flags any with a
later real starting point - don't assume they all match games/lines/
ratings just because those three do.
"""
import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

TEST_YEARS = [2013, 2015, 2017, 2019, 2021]

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)

with cfbd.ApiClient(configuration) as api_client:
    teams_api = cfbd.TeamsApi(api_client)
    recruiting_api = cfbd.RecruitingApi(api_client)
    rankings_api = cfbd.RankingsApi(api_client)
    coaches_api = cfbd.CoachesApi(api_client)
    games_api = cfbd.GamesApi(api_client)

    print(f"{'Year':<6} {'TeamATS':>9} {'Talent':>8} {'Recruit':>9} {'Rankings':>10} {'Coaches':>9} {'Weather':>9}")

    for year in TEST_YEARS:
        try:
            ats = teams_api.get_teams_ats(year=year)
            ats_n = len(ats)
        except Exception:
            ats_n = -1

        try:
            talent = teams_api.get_talent(year=year)
            talent_n = len(talent)
        except Exception:
            talent_n = -1

        try:
            recruiting = recruiting_api.get_team_recruiting_rankings(year=year)
            recruiting_n = len(recruiting)
        except Exception:
            recruiting_n = -1

        try:
            rankings = rankings_api.get_rankings(year=year)
            rankings_n = len(rankings)
        except Exception:
            rankings_n = -1

        try:
            coaches = coaches_api.get_coaches(min_year=year, max_year=year)
            coaches_n = len(coaches)
        except Exception:
            coaches_n = -1

        try:
            weather = games_api.get_weather(year=year)
            weather_n = len(weather)
        except Exception:
            weather_n = -1

        print(f"{year:<6} {ats_n:>9} {talent_n:>8} {recruiting_n:>9} {rankings_n:>10} {coaches_n:>9} {weather_n:>9}")

print("\n(-1 = call errored entirely; 0 = succeeded but returned nothing)")
print("\nNote: weekly point-in-time stats (end_week param) use the same underlying")
print("endpoints as team_stats/advanced_stats, already confirmed available at 2013.")
print("Offensive/defensive returning production and transfer portal/player data are")
print("deliberately NOT tested here - staying 2021+ per the transfer-portal-era decision.")