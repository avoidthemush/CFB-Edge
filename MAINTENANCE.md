# Annual Maintenance

Run once per offseason, before the new season's games start getting backfilled.

## How to run

1. Update `CURRENT_SEASON` in `app/config.py` to the new year
2. `python -m app.pipeline.annual_maintenance`
3. Review the final audit output - if it flags unresolved/unverified odds
   aliases, run `python -m app.pipeline.build_odds_crosswalk` and review
   manually (same process as the original 239-team build) before trusting
   live odds sync results for the new season

## What it does, and why (16 steps)

| Step | Why it's needed every year |
|---|---|
| 1. Venues | Cheap (no year param, 1 API call) - catches any new venues added to CFBD's catalog |
| 2. Teams | Conference realignment, new FBS additions/departures happen most offseasons |
| 3. Current season games | Populates the new season's schedule, keeps scores updated as games are played |
| 4. Odds API crosswalk | Only processes team names not already mapped - new/renamed programs need a name resolved to their CFBD team_id |
| 5. Ratings (SP+/SRS/Elo/FPI) | Preseason projections and in-season updates change throughout the year |
| 6. Advanced/adjusted stats | Recomputed as the season's games accumulate |
| 7. Team ATS | Against-the-spread record changes every week games are played |
| 8. Team talent | 247 composite score updates with new recruiting/portal activity |
| 9. Recruiting classes | New signing classes finalize each cycle |
| 10. Offensive returning production | Computed once per year based on prior season + new roster |
| 11. Player rosters | Full per-team pull (~686 teams) - this is the slow step (30-40+ min). Transfers, departures, new signees change every offseason |
| 12. Player season stats | New season's individual counting stats accumulate as games are played |
| 12.5. Player usage | Offensive skill-position usage rates, same cadence as player season stats |
| 13. Defensive returning production (calculated) | Our own metric, computed from players + player_season_stats already in the database - no API calls, instant |
| 14. Poll rankings | New weekly polls throughout the season |
| 15. Transfer portal | New entries throughout the year, especially at season's end and post-spring |
| 16. Coaches | New hires, coaching changes - pulls full career history each time, cheap (1 API call) |

Final audit prints row counts for every category above for the current
season, plus flags any unresolved/unverified Odds API crosswalk entries.

## Historical backfill (NOT part of annual maintenance)

Most sync modules also expose a `backfill_*()` function (e.g.
`backfill_games()`, `backfill_ratings()`) that re-walks the full
`HISTORICAL_START_YEAR` to `CURRENT_SEASON` range. Safe to re-run
(upserts, won't duplicate), but slower and unnecessary for routine
upkeep - the `sync_current_*()` functions annual_maintenance.py calls are
enough for yearly work. Only run a full backfill if historical data
integrity is in question.

## Known limitations

- **International venues**: `geocode_missing_venues.py` only geocodes US
  locations. A new international neutral-site venue (Dublin, Rio, etc.)
  will show up as "missing coordinates" in the audit - fix manually via
  the pattern in `fix_remaining_venues.py`. CFBD occasionally has
  city-name typos too, same manual-fix pattern applies.
- **Weather**: not yet part of annual maintenance - blocked on OpenWeather
  One Call 3.0/4.0 subscription setup. Will need both a historical and a
  live sync step added once unblocked.
- **Live odds / closing lines**: `sync_live_odds()` and
  `mark_closing_lines()` are NOT part of annual_maintenance.py - they're
  meant to run on a recurring schedule during the season (not yet built -
  see V1_CHECKLIST.md Section D), not as an annual/offseason step.

## Adding a new yearly step

When a new sync module is built that has an annual dimension, add it as a
new step in `app/pipeline/annual_maintenance.py`, update `run_final_audit()`
to report on it, and add a row to the table above - don't create a
separate one-off yearly script.