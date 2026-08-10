# Annual Maintenance

Run once per offseason, before the new season's games start getting backfilled.

## How to run

1. Update `CURRENT_SEASON` in `app/config.py` to the new year
2. `python -m app.pipeline.annual_maintenance`
3. Review the final audit output - if it flags unresolved/unverified odds
   aliases, run `python -m app.pipeline.build_odds_crosswalk` output review
   manually (same process as the original 184-team build) before trusting
   sync_odds.py results for the new season

## What it does, and why

| Step | Why it's needed every year |
|---|---|
| `sync_venues` | Cheap (no year param, 1 API call) - catches any new venues added to CFBD's catalog |
| `sync_teams(year=CURRENT_SEASON)` | Conference realignment, new FBS additions/departures happen most offseasons |
| `sync_current_season(year=CURRENT_SEASON)` | Populates the new season's schedule as it's released, then keeps scores updated as games are played |
| `build_odds_crosswalk` | Only processes team names it hasn't seen before - new/renamed programs need a name mapped to their CFBD team_id before odds can attach to their games |
| Final audit | Confirms nothing is silently broken (missing coordinates, unresolved team mappings, stub team count creeping up unexpectedly) |

## Historical backfill (NOT part of annual maintenance)

`python -m app.pipeline.sync_games` (calling `backfill_games()`) re-walks the
full `HISTORICAL_START_YEAR` to `CURRENT_SEASON` range. This is safe to
re-run (upserts, won't duplicate), but it's slower and unnecessary for
routine upkeep - `sync_current_season` alone is enough for yearly work.
Only run the full backfill if historical data integrity is in question.

## Adding a new yearly step

When a new sync module is built that has an annual dimension (ratings,
rankings, recruiting, etc.), add it as a new step in
`app/pipeline/annual_maintenance.py` and document it in the table above -
don't create a separate one-off yearly script.

## Known limitation: international venues

`geocode_missing_venues.py` only geocodes US locations (hardcoded `,US` in
the query). If CFBD adds a new international neutral-site venue (Dublin,
Rio de Janeiro, etc. - these do happen, e.g. the annual Aer Lingus College
Football Classic), the geocoder will fail to find it and it'll show up as
"missing coordinates" in the annual maintenance audit.

Fix: look up the coordinates manually and add them via a small one-off
script (see `fix_remaining_venues.py` for the pattern). Not worth
automating for the rare handful of international games per year.

CFBD occasionally has city-name typos too (e.g. "Aracata" instead of
"Arcata" for Cal Poly Humboldt) - same manual-fix pattern applies.