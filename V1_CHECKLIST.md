# Path to CFB Edge v1 — Data Readiness Checklist

Goal: everything on the data side genuinely ready before starting the
modeling phase. Organized by priority, not by when it was built.

## A. Must fix before v1 (real gaps, no workaround)

- [x] Bring annual_maintenance.py current (16+ steps, all sync scripts
      wired in, including team_season_stats added late as Step 6.5)
- [x] Update MAINTENANCE.md to match the current annual_maintenance.py steps
- [ ] Run one full annual_maintenance.py pass end-to-end, both machines
      (deliberately deferred until rest of checklist is done)
- [x] Resolve player_season_stats.usage_overall (populated, 22,210 rows)
- [x] Cross-table integration check (caught and fixed the
      offensive_returning_production silent-duplicate-table bug -
      this check earned its place on the list)

## B. Should validate before v1 (untested code paths)

- [x] Run sync_live_odds() for real (185 rows, DK+FanDuel, 0 unmatched
      teams/games - also caught and fixed a decimal-vs-American odds
      format bug in the process)
- [ ] Run mark_closing_lines() for real - BLOCKED, not by us: needs a
      tracked game to have actually kicked off. Season starts Aug 29.
      Cannot be tested before then regardless of effort. Revisit once
      Week 1 games are underway.
- [x] Confirm class_year is safe to ignore for now (documented in
      DESIGN_DECISIONS.md as unresolved - excluded from any feature work
      until investigated)

## C. Explicitly deferred (documented, acceptable to leave for now)

- [x] Weather (historical) - RESOLVED, better than planned: CFBD's own
      get_weather endpoint has real historical weather tied directly to
      games (temp, wind, precip, snowfall, humidity, pressure, condition)
      - no OpenWeather paid subscription needed at all. 13,719 rows
      across 2021-2025 (2021 has a known ~35% coverage gap, documented in
      DESIGN_DECISIONS.md - genuine CFBD historical limitation, not a bug).
- [ ] Weather (live/upcoming) - sync_weather_for_upcoming_games() is
      built and uses the existing free OpenWeather key (~5 day forecast
      window). Not yet validated with a real run, since no games are
      within the forecast window until closer to Aug 29 kickoff. Revisit
      once Week 1 approaches.
- [ ] Betting line provider-priority fallback logic (Bovada -> DraftKings
      -> other) - correctly belongs in feature engineering, not data
      gathering
- [ ] Game-level player stats - deliberately out of scope, revisit only
      if modeling reveals a real need

## D. Operational readiness (post-v1, not blocking data completeness)

- [ ] Railway scheduler for recurring jobs
- [ ] Odds polling cadence implementation

## E. Nice-to-have

- [ ] Data dictionary
- [x] Final row-count snapshot across all tables

## Final row-count baseline (Aug 13, 2026)

| Table | Rows |
|---|---|
| teams | 756 |
| venues | 844 |
| coaches | 300 |
| coach_seasons | 893 |
| games | 19,163 |
| odds_snapshots | 185 |
| cfbd_betting_lines | 17,544 |
| weather_snapshots | 0 (blocked - see Section C) |
| team_season_stats | 41,829 |
| team_advanced_stats | 664 |
| rating_snapshots | 3,313 |
| team_ats | 1,227 |
| team_talent | 962 |
| recruiting_classes | 1,199 |
| offensive_returning_production | 792 |
| defensive_returning_production | 1,393 |
| transfer_portal_entries | 18,862 |
| poll_rankings | 9,357 |
| team_source_aliases | 239 |
| players | 65,604 |
| player_season_stats | 67,741 |
| **TOTAL** | **252,867** |

## Section A/B addendum

- [x] team_season_stats added (discovered as a genuine gap during the
      row-count review, not originally tracked - raw box-score stats,
      63 categories including direct turnovers/turnoversOpponent fields,
      41,829 rows, wired into annual_maintenance.py as Step 6.5)

## Definition of done for v1

All of Section A checked, all of Section B checked or consciously
accepted as a known gap, Section C explicitly acknowledged as deferred
(not forgotten), and Section D/E logged as intentional post-v1 work -
not silently skipped.

## Status: data-gathering phase complete except Section C (explicitly deferred)

Sections A and B are done except two items intentionally left open:
running the full annual_maintenance.py end-to-end (deferred by choice -
nothing to gain from running it now vs. as the final validation step),
and mark_closing_lines() validation (blocked by the calendar - no games
have kicked off yet, season starts Aug 29).

Section C (weather, provider-priority fallback logic, game-level player
stats) remains intentionally deferred, documented, and tracked - not
forgotten. Section D (scheduler, polling cadence) and E (data dictionary)
remain open as post-v1/nice-to-have work.

Ready to move toward the modeling phase (v2) with these known, accepted
gaps carried forward openly rather than discovered mid-build.