# Data Build Checklist

Tracks sync status for every table in the schema. Update as we go.

## Done
- [x] venues (844, full coordinates)
- [x] teams (686 verified + 70 stubs)
- [x] games (19,163, 2021-2026)
- [x] team_source_aliases / Odds API crosswalk (239, fully verified)
- [x] cfbd_betting_lines (17,544 rows, 2021-2026, 10 providers)
- [x] odds_snapshots (live sync built, DK/FanDuel only - not yet run on a schedule)
- [x] rating_snapshots (SP+, SRS, Elo, FPI - 2021-2026)
- [x] team_advanced_stats (opponent-adjusted efficiency, JSONB - 2021-2025, 2026 empty as expected)

## Deferred
- [ ] weather_snapshots - needs OpenWeather One Call 3.0/4.0 subscription
      (separate signup + billing, user will set up account and provide
      access when ready). Need BOTH historical (2021-2025 backfill) and
      live (game-week forecasts) once unblocked.

## Not started
- [ ] team_ats (against-the-spread records)
- [ ] team_talent (247 composite score)
- [ ] recruiting_classes
- [ ] returning_production
- [ ] transfer_portal_entries
- [ ] poll_rankings (AP/Coaches/CFP)
- [ ] coaches