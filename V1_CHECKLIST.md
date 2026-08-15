# Path to CFB Edge v1 — Data Readiness Checklist

Goal: everything on the data side genuinely ready before starting the
modeling phase. Organized by priority, not by when it was built.

## UPDATED BASELINE (Aug 13, 2026) — supersedes the original checkpoint below

Original v1-data-complete (Aug 12, 2026) covered 2021-2026, 252,867 rows.
That checkpoint is preserved as a git tag for historical reference, but
is NO LONGER the current standard - this update is.

**What changed:** during initial Spread model validation, an ATS
backtest revealed no statistically reliable edge, and the small sample
size (a few thousand FBS games) made it impossible to tell real signal
from noise. Rather than guess, we verified CFBD's actual historical data
availability (see check_full_historical_scope.py,
check_player_data_historical.py) and extended the historical range
accordingly - not to an assumed year, but to the real, confirmed
boundary for each source:

- **2015**: project-wide floor. Games, betting lines, ratings, advanced
  stats, team season stats, weekly point-in-time stats, recruiting,
  rankings, coaches, weather, rosters, player season stats, player
  usage, and offensive returning production all genuinely support this.
- **2019**: team ATS - confirmed unavailable before this (not a choice).
- **2021**: transfer portal entries only - confirmed unavailable before
  this (not a choice; this was previously, incorrectly, assumed to
  apply to ALL player-level data - corrected this session).

**New row-count baseline (Aug 13, 2026):**

| Table | Rows |
|---|---|
| teams | 774 |
| venues | 844 |
| coaches | 394 |
| coach_seasons | 1,708 |
| games | 28,105 |
| odds_snapshots | 185 |
| cfbd_betting_lines | 33,903 |
| weather_snapshots | 18,620 |
| team_season_stats | 89,999 |
| team_advanced_stats | 1,438 |
| rating_snapshots | 27,201 |
| team_ats | 1,493 |
| team_talent | 2,275 |
| recruiting_classes | 2,559 |
| offensive_returning_production | 1,566 |
| defensive_returning_production | 2,606 |
| transfer_portal_entries | 18,862 |
| poll_rankings | 18,366 |
| team_source_aliases | 239 |
| players | 100,455 |
| player_season_stats | 122,459 |
| team_stats_weekly | 1,301,348 |
| team_advanced_stats_weekly | 21,013 |
| coach_tendencies | 2,748 |
| **TOTAL** | **1,799,160** |

**Known issue caught and fixed during this extension:** backfill_to_2015.py
initially omitted sync_coaches() entirely (coaches don't need a per-year
loop, one call pulls full career history - this was a pure oversight,
not a limitation). Caught via a sanity check on coach_tendencies output
being suspiciously identical to the pre-extension run. Fixed via
fix_missing_coaches_backfill.py; backfill_to_2015.py itself updated so
the script is an accurate record going forward.

---

# Path to CFB Edge v1 — Data Readiness Checklist (original, Aug 12 2026)

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
- [x] Weekly point-in-time stats layer added (team_stats_weekly,
      team_advanced_stats_weekly, Elo via rating_snapshots.week) -
      built to support leakage-safe model features per
      V2_MODEL_PLAN.md Section 4. ~750K rows across 2021-2025,
      verified monotonically increasing per team per week.
- [x] Coach tendency profiles added (coach_tendencies table) -
      recency-weighted style/pace/havoc profile per coach, computed
      only from seasons strictly before the target year (leakage-safe).
      1,085 rows computed, 715 correctly skipped (coaches with no
      qualifying prior data). First-time HCs deliberately get no row -
      falls back to neutral in the blend, no special-case logic needed.

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

- [ ] Odds polling cadence implementation
- [ ] Railway scheduler for recurring jobs - NOW A HARD DEPENDENCY (not
      just nice-to-have): the model's point-in-time blending approach
      (see V2_MODEL_PLAN.md Section 4) requires weekly stats/advanced-
      stats/Elo syncs to run during the live season for 2026 predictions
      to work at all.
- [ ] Railway scheduler for recurring jobs - HARD DEPENDENCY: the
      model's point-in-time blending approach (V2_MODEL_PLAN.md Section
      4) requires weekly stats/advanced-stats/Elo syncs AND weather
      syncs to run during the live season for 2026 predictions to work
      at all. Coach tendencies can be recomputed less frequently (only
      changes with new coaching hires or newly-completed seasons) but
      should be refreshed whenever a coaching change is detected.
- [ ] Live odds collection scope updated (Aug 2026): sync_live_odds()
      now pulls ALL available US-region bookmakers, not just DK/FanDuel
      - confirmed zero extra API cost. Usage remains DK/FanDuel-only via
      get_game_line.py's LIVE_BOOK_PRIORITY. Once the scheduler runs
      this regularly, odds_snapshots will accumulate a genuinely
      complete multi-book historical archive, not just a DK/FanDuel one.

## E. Nice-to-have

- [ ] Data dictionary
- [x] Final row-count snapshot across all tables

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