"""
Probes how far back CFBD's data actually goes for each source we care
about, before committing to any backfill. Checks a spread of years
rather than assuming - advanced stats/PPA and SP+ in particular have a
real historical start point that isn't "always existed."
"""
import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

TEST_YEARS = [2005, 2008, 2010, 2012, 2013, 2014, 2015, 2016, 2018, 2020]

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)

with cfbd.ApiClient(configuration) as api_client:
    games_api = cfbd.GamesApi(api_client)
    betting_api = cfbd.BettingApi(api_client)
    ratings_api = cfbd.RatingsApi(api_client)
    stats_api = cfbd.StatsApi(api_client)

    print(f"{'Year':<6} {'Games':>8} {'Lines':>8} {'SP+':>8} {'Elo':>8} {'AdvStats':>10} {'TeamStats':>10}")

    for year in TEST_YEARS:
        try:
            games = games_api.get_games(year=year)
            games_n = len(games)
        except Exception:
            games_n = -1

        try:
            lines = betting_api.get_lines(year=year)
            lines_n = sum(1 for g in lines if getattr(g, "lines", None))
        except Exception:
            lines_n = -1

        try:
            sp = ratings_api.get_sp(year=year)
            sp_n = len(sp)
        except Exception:
            sp_n = -1

        try:
            elo = ratings_api.get_elo(year=year)
            elo_n = len(elo)
        except Exception:
            elo_n = -1

        try:
            adv = stats_api.get_advanced_season_stats(year=year)
            adv_n = len(adv)
        except Exception:
            adv_n = -1

        try:
            team_stats = stats_api.get_team_stats(year=year)
            team_stats_n = len(team_stats)
        except Exception:
            team_stats_n = -1

        print(f"{year:<6} {games_n:>8} {lines_n:>8} {sp_n:>8} {elo_n:>8} {adv_n:>10} {team_stats_n:>10}")

print("\n(-1 means the call errored entirely; 0 means it succeeded but returned nothing)")