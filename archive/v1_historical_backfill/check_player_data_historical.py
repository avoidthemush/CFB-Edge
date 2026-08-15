"""
Checks the REAL historical boundary for each player-level data source
separately, rather than assuming they're all bound by the transfer
portal's 2021 start - only transfer_portal_entries actually is.
"""
import os
import cfbd
from dotenv import load_dotenv

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

TEST_YEARS = [2013, 2015, 2017, 2019, 2020, 2021]

configuration = cfbd.Configuration(access_token=CFBD_API_KEY)

with cfbd.ApiClient(configuration) as api_client:
    teams_api = cfbd.TeamsApi(api_client)
    stats_api = cfbd.StatsApi(api_client)
    players_api = cfbd.PlayersApi(api_client)

    print(f"{'Year':<6} {'Roster':>8} {'PlayerStats':>12} {'PlayerUsage':>12} {'ReturnProd':>11} {'TransferPortal':>15}")

    for year in TEST_YEARS:
        try:
            roster = teams_api.get_roster(team="Alabama", year=year)
            roster_n = len(roster)
        except Exception:
            roster_n = -1

        try:
            player_stats = stats_api.get_player_season_stats(year=year, team="Alabama")
            player_stats_n = len(player_stats)
        except Exception:
            player_stats_n = -1

        try:
            usage = players_api.get_player_usage(year=year, team="Alabama")
            usage_n = len(usage)
        except Exception:
            usage_n = -1

        try:
            rp = players_api.get_returning_production(year=year, team="Alabama")
            rp_n = len(rp)
        except Exception:
            rp_n = -1

        try:
            portal = players_api.get_transfer_portal(year=year)
            portal_n = len(portal)
        except Exception:
            portal_n = -1

        print(f"{year:<6} {roster_n:>8} {player_stats_n:>12} {usage_n:>12} {rp_n:>11} {portal_n:>15}")

print("\n(-1 = call errored entirely; 0 = succeeded but returned nothing)")
print("Roster/PlayerStats/Usage/ReturnProd tested on Alabama only (single team, cheap probe)")
print("TransferPortal has no team filter - tested at full league scope")