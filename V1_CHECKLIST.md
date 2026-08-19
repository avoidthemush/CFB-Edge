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

**Note (Aug 18, 2026):** since this baseline was set, V2 model work
confirmed that market_spread_open (and moneyline) coverage only
genuinely starts at 2021, not 2015-2019 - see V2_SPREAD_FEATURE_LOG.md.
This doesn't invalidate the 2015 floor (that data remains valuable for
ratings/stats/coach history, used successfully throughout V2), it just
means "2015 floor" and "2021 floor for anything requiring a real
opening line" are both true, for different purposes.

---

# Path to CFB Edge v1 — Data Readiness Checklist (original, Aug 12 2026)

## A. Must fix before v1 (real gaps, no workaround)

- [x] Bring annual_maintenance.py current (16+ steps, all sync scripts
      wired in, including team_season_stats added late as Step 6.5)
- [x] Update MAINTENANCE.md to match the current annual_maintenance.py steps
- [ ] Run one full annual_maintenance.py pass end-to-end, both machines
      — MOVED to FINAL_ROLLOUT_CHECKLIST.md (deliberately deferred to
      pre-launch, not a V1-blocking gap)
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
- [ ] Run mark_closing_lines() for real - STILL BLOCKED, not by us:
      needs a tracked game to have actually kicked off. Season starts
      Aug 29, 2026. Cannot be tested before then regardless of effort.
      Confirmed still blocked as of Aug 18, 2026 - revisit once Week 1
      games are underway.
- [x] Confirm class_year is safe to ignore for now (documented in
      DESIGN_DECISIONS.md as unresolved - excluded from any feature work
      until investigated; remained correctly excluded throughout all of
      V2 model-building)

## C. Explicitly deferred (documented, acceptable to leave for now)

- [x] Weather (historical) - RESOLVED, better than planned: CFBD's own
      get_weather endpoint has real historical weather tied directly to
      games (temp, wind, precip, snowfall, humidity, pressure, condition)
      - no OpenWeather paid subscription needed at all. 13,719 rows
      across 2021-2025 (2021 has a known ~35% coverage gap, documented in
      DESIGN_DECISIONS.md - genuine CFBD historical limitation, not a bug).
      Used successfully as a real feature (wind_mph specifically) in
      approved Total systems (Wind Deviation) during V2.
- [ ] Weather (live/upcoming) - sync_weather_for_upcoming_games() is
      built and uses the existing free OpenWeather key (~5 day forecast
      window). STILL not validated with a real run as of Aug 18, 2026 -
      no games are within the forecast window until closer to Aug 29
      kickoff. Confirmed still blocked by the calendar, not by effort.
- [x] Betting line provider-priority fallback logic (Bovada -> DraftKings
      -> other) - correctly belongs in feature engineering, not data
      gathering. BUILT during V2: get_game_line.py's
      get_best_line_for_game() (historical, CFBD-priority) and
      get_live_book_lines() (live, DK/FanDuel-specific, added after a
      real stale-line bug was caught and fixed) - both verified working
      in production across all three models (Spread, Total, Moneyline).
- [ ] Game-level player stats - deliberately out of scope, revisit only
      if modeling reveals a real need. Confirmed still not needed as of
      end of V2 - no model required this.

## D. Operational readiness (post-v1, not blocking data completeness)

- [ ] Odds polling cadence implementation - STILL OPEN, this is core
      V3 scheduler work, not started.
- [ ] Railway scheduler for recurring jobs - HARD DEPENDENCY (confirmed,
      not just theoretical, during V2): the model's point-in-time
      blending approach requires weekly stats/advanced-stats/Elo syncs
      AND weather syncs to run during the live season for 2026
      predictions to work at all. Coach tendencies can be recomputed
      less frequently (only changes with new coaching hires or newly-
      completed seasons) but should be refreshed whenever a coaching
      change is detected. STILL NOT BUILT as of Aug 18, 2026 - this is
      V3's primary focus.
- [x] Live odds collection scope updated (Aug 2026): sync_live_odds()
      now pulls ALL available US-region bookmakers, not just DK/FanDuel
      - confirmed zero extra API cost. BUILT and confirmed during V2.
      Usage remains DK/FanDuel-only via get_live_book_lines()'s
      LIVE_BOOK_PRIORITY constant. The scheduler (still not built) is
      what's needed for this to accumulate a genuinely complete
      multi-book historical archive on a recurring basis - the
      collection LOGIC is done, the recurring EXECUTION is not.
- [ ] Open/live/close line-state tracking (NEW, identified during V2,
      Aug 17-18 2026) - kickoff-aware split of odds_snapshots into
      opening/live/closing states. Logged in full in
      V3_DASHBOARD_PLAN.md - real scheduler design requirement
      (polling frequency must increase near kickoff), not yet built.

## E. Nice-to-have

- [ ] Data dictionary - still not built, still genuinely optional,
      not blocking anything.
- [x] Final row-count snapshot across all tables

## Section A/B addendum

- [x] team_season_stats added (discovered as a genuine gap during the
      row-count review, not originally tracked - raw box-score stats,
      63 categories including direct turnovers/turnoversOpponent fields,
      41,829 rows, wired into annual_maintenance.py as Step 6.5). Used
      successfully as a real feature (turnover_margin, third-down rate)
      in Spread/Total model-building during V2.

## Definition of done for v1

All of Section A checked, all of Section B checked or consciously
accepted as a known gap, Section C explicitly acknowledged as deferred
(not forgotten), and Section D/E logged as intentional post-v1 work -
not silently skipped.

## STATUS (updated Aug 18, 2026, after full V2 completion): Phase 1 (data) confirmed genuinely ready

Reviewed line-by-line after completing V2 (all three models: Spread,
Total, Moneyline - 7 approved systems total) to confirm nothing was
silently gapped. Result:

- **Section A:** fully done except one item, deliberately moved to
  FINAL_ROLLOUT_CHECKLIST.md (annual_maintenance.py full run - a
  pre-launch validation step, not a V1 gap).
- **Section B:** fully done except mark_closing_lines(), which remains
  genuinely calendar-blocked (needs a real kickoff, season starts Aug
  29) - not a gap, just not yet reachable.
- **Section C:** historical weather and provider-fallback logic both
  CONFIRMED DONE (the latter was actually built during V2 and never
  checked off here until now). Live weather forecast validation and
  game-level player stats remain correctly deferred - the former by
  calendar, the latter by genuine lack of need.
- **Section D:** the real, honest gap. Scheduler, polling cadence, and
  the newly-identified open/live/close line tracking are ALL still
  unbuilt - this is V3's actual scope, correctly nothing has been
  skipped here, it's just not V3 yet.
- **Section E:** data dictionary still open, still optional.

**Conclusion: Phase 1 (data) is genuinely, fully ready for Phase 3 (V3)
to build on.** No hidden gaps found during this review - the only open
items are either calendar-blocked (nothing to do about it yet),
deliberately moved to the cross-phase rollout checklist, or explicitly
in V3's own scope (the scheduler itself).