from collections import defaultdict

from app.db import SessionLocal
from app.models import PlayerSeasonStat, Team, Player, DefensiveReturningProduction
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR


def _safe_pct(part, whole):
    return (part / whole) if whole and whole > 0 else None


def calc_defensive_returning_production():
    """
    Pure computation from data already in our database - no API calls,
    free and instant to re-run. 'Returning' is normally determined via
    player_season_stats (preserves per-year team membership correctly).

    Exception: for any year with ZERO player_season_stats rows at all
    (i.e. the season hasn't been played yet - true for 2026 as of this
    build), stats can't tell us who's on the roster. We fall back to
    players.team_id (current known roster) for that year only - safe
    because it only applies when no year-specific stats exist anywhere,
    so it never overrides real historical data for a past season.
    """
    db = SessionLocal()

    rows = db.query(
        PlayerSeasonStat.player_id,
        PlayerSeasonStat.team_id,
        PlayerSeasonStat.year,
        PlayerSeasonStat.tackles_for_loss,
        PlayerSeasonStat.passes_defended,
        PlayerSeasonStat.fumbles_recovered,
    ).all()

    by_team_year = defaultdict(dict)
    years_with_any_stats = set()
    for player_id, team_id, year, tfl, pd, fumrec in rows:
        years_with_any_stats.add(year)
        if team_id is None:
            continue
        by_team_year[(team_id, year)][player_id] = (tfl or 0.0, pd or 0.0, fumrec or 0.0)

    # Roster fallback: current team_id per player, for years with no stats
    roster_team_by_player = {p.id: p.team_id for p in db.query(Player.id, Player.team_id).all()}

    teams = db.query(Team).filter(Team.is_verified == True).all()
    inserted = 0
    updated = 0
    skipped_no_prior_data = 0
    used_roster_fallback = 0

    for team in teams:
        for year in range(HISTORICAL_START_YEAR + 1, CURRENT_SEASON + 1):
            prior_year = year - 1
            prior_players = by_team_year.get((team.id, prior_year), {})

            if not prior_players:
                skipped_no_prior_data += 1
                continue

            if year in years_with_any_stats:
                current_player_ids = set(by_team_year.get((team.id, year), {}).keys())
            else:
                # No stats exist for this year anywhere - season hasn't
                # been played. Fall back to current roster membership.
                current_player_ids = {
                    pid for pid, team_id in roster_team_by_player.items() if team_id == team.id
                }
                used_roster_fallback += 1

            total_tfl = sum(v[0] for v in prior_players.values())
            total_pd = sum(v[1] for v in prior_players.values())
            total_fum = sum(v[2] for v in prior_players.values())
            total_havoc = total_tfl + total_pd + total_fum

            returning_tfl = returning_pd = returning_fum = 0.0
            returning_count = 0

            for player_id, (tfl, pd, fumrec) in prior_players.items():
                if player_id in current_player_ids:
                    returning_tfl += tfl
                    returning_pd += pd
                    returning_fum += fumrec
                    returning_count += 1

            returning_havoc = returning_tfl + returning_pd + returning_fum

            fields = dict(
                total_tfl_prior_year=total_tfl,
                total_pd_prior_year=total_pd,
                total_fumbles_rec_prior_year=total_fum,
                total_havoc_prior_year=total_havoc,
                tfl_returning=returning_tfl,
                pd_returning=returning_pd,
                fumbles_rec_returning=returning_fum,
                havoc_returning=returning_havoc,
                percent_tfl_returning=_safe_pct(returning_tfl, total_tfl),
                percent_pd_returning=_safe_pct(returning_pd, total_pd),
                percent_fumbles_rec_returning=_safe_pct(returning_fum, total_fum),
                percent_havoc_returning=_safe_pct(returning_havoc, total_havoc),
                players_prior_year_count=len(prior_players),
                players_returning_count=returning_count,
            )

            existing = db.query(DefensiveReturningProduction).filter(
                DefensiveReturningProduction.team_id == team.id,
                DefensiveReturningProduction.year == year,
            ).first()

            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                db.add(DefensiveReturningProduction(team_id=team.id, year=year, **fields))
                inserted += 1

    db.commit()
    db.close()
    print(f"Defensive returning production: inserted {inserted}, updated {updated} "
          f"(skipped {skipped_no_prior_data} team-years with no prior-year data, "
          f"used roster fallback for {used_roster_fallback} team-years)")


if __name__ == "__main__":
    calc_defensive_returning_production()