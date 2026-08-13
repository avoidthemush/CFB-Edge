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
- [x] team_ats (against-the-spread records)
- [x] team_talent (247 composite score - 2021-2025, count variance across years confirmed legitimate)
- [x] recruiting_classes (2021-2026, uses shared team_resolver.py for CFBD naming inconsistencies)
- [x] returning_production (offense-side, full 12-field CFBD data - 2021-2026)
- [x] players (65,604 after cleanup - roster bio data 2021-2026, has_complete_bio flag for ~5.8% with thin CFBD data)
- [x] offensive_returning_production (renamed from returning_production, offense-side only, full CFBD field set)
- [x] defensive_returning_production (custom havoc-rate-based metric - TFL + passes defended + fumbles recovered, verified against NCAA official stat definitions to avoid double-counting)
- [x] players (65,604 after cleanup)
- [x] player_season_stats (67,741 rows, defensive + offensive counting stats)
- [x] poll_rankings (AP/Coaches/CFP - 2021-2026, 2026 currently has Week 1 Coaches Poll preseason rankings)
- [x] transfer_portal_entries (18,862 rows, 2021-2026, delete-and-replace pattern since CFBD provides no stable entry ID)
- [x] coaches / coach_seasons (300 coaches, 893 coach-seasons, includes SP+ ratings per coach-season)


## Deferred
- [ ] weather_snapshots - needs OpenWeather One Call 3.0/4.0 subscription
      (separate signup + billing, user will set up account and provide
      access when ready). Need BOTH historical (2021-2025 backfill) and
      live (game-week forecasts) once unblocked.

## Not started