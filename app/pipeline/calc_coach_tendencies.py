from collections import defaultdict

from app.db import SessionLocal
from app.models import Coach, CoachSeason, TeamAdvancedStat, CoachTendency
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

RECENCY_DECAY = 0.7  # each season back gets 70% the weight of the one after it - first-pass estimate, adjustable


def _get(d, *path):
    for key in path:
        if d is None:
            return None
        d = d.get(key)
    return d


def calc_coach_tendencies(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    """
    Pure computation from data already in the database - no API calls.
    For every (coach, year) in [start_year, end_year] where that coach
    has at least one PRIOR season on record, builds a recency-weighted
    style profile from that prior data only. A coach's first-ever season
    produces no row at all (zero prior data = no profile, per design -
    falls back to neutral).
    """
    db = SessionLocal()

    coach_seasons = db.query(CoachSeason).order_by(CoachSeason.coach_id, CoachSeason.year).all()
    by_coach = defaultdict(list)
    for cs in coach_seasons:
        by_coach[cs.coach_id].append(cs)

    adv_stats_lookup = {
        (row.team_id, row.year): row.raw_json
        for row in db.query(TeamAdvancedStat).all()
    }

    inserted = 0
    updated = 0
    skipped_no_prior = 0

    for coach_id, seasons in by_coach.items():
        for target_year in range(start_year, end_year + 1):
            prior_seasons = [s for s in seasons if s.year < target_year and s.team_id is not None]

            if not prior_seasons:
                skipped_no_prior += 1
                continue

            prior_seasons.sort(key=lambda s: s.year, reverse=True)

            weighted_sums = defaultdict(float)
            weight_total = 0.0
            used = 0

            for i, cs in enumerate(prior_seasons):
                stats = adv_stats_lookup.get((cs.team_id, cs.year))
                if stats is None:
                    continue

                weight = RECENCY_DECAY ** i
                weight_total += weight
                used += 1

                pass_rate = _get(stats, "offense", "passingPlays", "rate")
                off_sr = _get(stats, "offense", "successRate")
                off_sr_pass = _get(stats, "offense", "passingPlays", "successRate")
                off_sr_rush = _get(stats, "offense", "rushingPlays", "successRate")
                off_expl = _get(stats, "offense", "explosiveness")
                def_havoc = _get(stats, "defense", "havoc", "total")
                def_ppo = _get(stats, "defense", "pointsPerOpportunity")

                for key, val in [
                    ("pass_rate", pass_rate), ("off_success_rate", off_sr),
                    ("off_success_rate_pass", off_sr_pass), ("off_success_rate_rush", off_sr_rush),
                    ("off_explosiveness", off_expl), ("def_havoc_rate", def_havoc),
                    ("def_points_per_opportunity", def_ppo),
                ]:
                    if val is not None:
                        weighted_sums[key] += val * weight

            if used == 0 or weight_total == 0:
                skipped_no_prior += 1
                continue

            fields = {k: (v / weight_total) for k, v in weighted_sums.items()}

            existing = db.query(CoachTendency).filter(
                CoachTendency.coach_id == coach_id,
                CoachTendency.as_of_year == target_year,
            ).first()

            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                existing.seasons_used = used
                updated += 1
            else:
                db.add(CoachTendency(
                    coach_id=coach_id, as_of_year=target_year, seasons_used=used, **fields
                ))
                inserted += 1

    db.commit()
    db.close()
    print(f"Coach tendencies: inserted {inserted}, updated {updated} (skipped {skipped_no_prior} - no prior data)")


def calc_current_coach_tendencies(year: int = CURRENT_SEASON):
    """Annual-maintenance-friendly version - recomputes tendencies for just the current year."""
    calc_coach_tendencies(start_year=year, end_year=year)


if __name__ == "__main__":
    calc_coach_tendencies()