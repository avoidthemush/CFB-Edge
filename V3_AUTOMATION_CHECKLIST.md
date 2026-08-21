# V3 — Automation Checklist

Tactical build order for V3's automation layer, built before the
dashboard (which just reads whatever automation produces). Each item
gets designed, built, and verified before moving to the next - same
discipline as V2.

## 1. Odds polling
- [ ] Scheduler job: poll Odds API /odds endpoint every 5 minutes, flat
      interval (confirmed: one call returns the full slate, cost is
      per-call not per-game; 8,928 calls/month at this rate, ~11k
      headroom out of 20k budget)
- [ ] Confirmed: flat 5-min interval satisfies open/live/close design
      without needing variable/ramping frequency - real simplification,
      no extra complexity needed here
- [ ] Deploy as an actual Railway service/worker, not run locally (per
      V3_DASHBOARD_PLAN.md deployment note)
- [ ] Open/live/close line-state logic: kickoff-aware split of stored
      snapshots (design already logged in V3_DASHBOARD_PLAN.md, not
      yet built)

## 2. Weekly stats/data sync automation
- [ ] Schedule sync_weekly_stats.py, sync_advanced_stats.py, etc. to
      run automatically after each week's games complete
- [ ] VERIFY (cannot fully test until Week 1 completes, real season-
      gated item): live-synced weekly data lands in the SAME tables/
      schema used throughout V2 training - expected to be correct by
      construction, needs real confirmation once live data exists
- [ ] Full annual_maintenance.py end-to-end run (moved here from
      FINAL_ROLLOUT_CHECKLIST.md as the natural place to validate it -
      this IS the automation being tested)

## 3. Prediction refresh architecture (decoupled, for speed)
- [ ] DECOUPLE team-strength predictions (weekly cadence, ~2 min cost -
      FeatureCache + model inference) from market-qualification checks
      (5-min cadence, must be near-instant - pure comparison against
      already-computed predictions, no feature rebuild)
- [ ] Design: where do "already-computed team predictions" get cached/
      stored between the weekly run and each 5-min qualification check?
      (Real DB table vs. in-memory service state - needs a decision)
- [ ] Verify real runtime: full slate qualification check should run in
      well under a minute, ideally seconds, once decoupled

## 4. Trailing "last N games" data layer (ATS, ML, Total record)
- [ ] Build rolling last-10-games ATS/ML/Total record per team,
      computed from games + cfbd_betting_lines + odds_snapshots
- [ ] MUST correctly cross season boundaries (Week 1-2 of a new season
      needs to reach back into the prior season's final games to reach
      10) - explicit design requirement, not an edge case
- [ ] Decide: materialized/stored table (faster reads, needs its own
      refresh cadence) vs. computed on-demand (always fresh, slower)

## 5. Data requirements for the (later) dashboard bet sheet
Not built now - noting what automation must expose cleanly so this is
easy later, not a redesign:
- [ ] Per-game: Spread/Total/ML at BOTH books (DK, FanDuel), separately
- [ ] Per-game: relevant advanced stats (whatever the approved systems
      actually use - pace, field position, etc.)
- [ ] Per-game: venue + weather
- [ ] FBS-vs-FBS only, confirmed as a hard filter throughout (already
      built into all three predict_week.py scripts)

## Open architectural questions (resolve before building)
- Scheduler implementation: Railway cron jobs (separate scheduled
  tasks) vs. one persistent worker process managing all three cadences
  internally?
- Where do decoupled team-predictions get stored between weekly runs
  and 5-min checks - new table, or reuse model_predictions with a
  "last computed" flag?

  
## Architectural decisions RESOLVED (Aug 2026)

**Scheduler implementation:** Railway cron jobs, one per cadence (odds
poll, weekly stats sync, weekly feature-cache refresh) - not a
persistent worker. No task needs in-memory state between runs; the
database (specifically the new game_feature_cache table) IS the shared
state. Simpler, uses Railway's built-in scheduling rather than
reimplementing it.

**Decoupled prediction storage:** NEW game_feature_cache table - caches
the full build_game_features() output (JSON) per game, refreshed
weekly. The 5-min odds-polling job reads this cache and checks fresh
lines against it - no feature rebuild, no model re-inference, just
comparison math. Built: app/models.py (GameFeatureCache),
app/pipeline/refresh_game_feature_cache.py (weekly refresh job).

## Next: build the 5-min market-check job that reads this cache instead
of calling build_game_features() directly - this is what makes the
5-minute cadence actually fast.


## Section 3 status update (Aug 18, 2026)
- [x] Decoupled architecture BUILT and VERIFIED: game_feature_cache
      table + weekly refresh_game_feature_cache.py (~5s for a 51-game
      slate) + batched get_live_book_lines_batch() (one query for the
      whole slate, not per-game).
- [x] Real runtime confirmed: all three predict_week.py scripts run in
      11-17s total, comfortably under a minute, well within the 5-min
      polling cadence. Verified output identical to pre-refactor
      baseline (same picks, same write counts) - pure performance fix,
      zero behavioral change.
- [x] Real bug found and fixed along the way: Windows Application
      Control policy blocked pandas' compiled DLL from loading in
      Spread's predict_week.py - fixed by removing the pandas
      dependency entirely (only needed a single-row transform, plain
      Python lists work identically).

## Section 1 status update (Aug 21, 2026) — LIVE AND CONFIRMED WORKING

- [x] Railway cron job deployed and CONFIRMED running successfully on
      the real 5-min schedule. First live run: 111 events pulled, 738
      rows inserted, 0 unmatched teams/games, 1.0s total runtime -
      enormous headroom under the 5-min window. Build correctly cached
      (no pip install on cron runs, only on actual code/dependency changes).
- [ ] Minor cleanup (not urgent): datetime.utcnow() deprecation
      warnings in run_odds_poll.py - harmless today, worth switching to
      datetime.now(datetime.UTC) at some point.
- [ ] Minor cleanup (not urgent): sync_live_odds() could return a real
      summary dict instead of None, for more informative cron logs.


## Section 2 status update (Aug 21, 2026) — LIVE AND CONFIRMED WORKING

- [x] Daily sync cron job built (app/pipeline/run_daily_sync.py) and
      deployed to Railway: weekly stats -> advanced stats -> rankings
      -> ratings -> feature cache refresh, chained in dependency order.
      Confirmed running successfully at 2am UTC daily. Local test: 158.9s
      total. Railway production run: 34.2s total (faster - Railway-to-
      Railway network path, as anticipated).
- [x] Real design decision: DAILY (not weekly) cadence chosen - CFB games
      happen on non-weekend days too (Tue/Wed MAC games), and daily is
      more resilient to CFBD's own data-finalization lag than a fixed
      weekly day would be.
- [ ] Minor cleanup (batched, not urgent): datetime.utcnow() deprecation
      warnings appear in BOTH run_odds_poll.py and run_daily_sync.py -
      fix both together in one pass (switch to datetime.now(datetime.UTC))
      rather than one at a time.


## Known performance issue to fix (found Aug 21, 2026)
- [ ] refresh_team_recent_form.py took 307.5s (dominant cost in the
      daily chain, more than doubling total runtime 158.9s -> 456.1s).
      Likely cause: grade_game_for_team() calls get_best_line_for_game()
      per-game per-team (up to 1,380 individual DB queries) - same
      per-item-query performance mistake already found and fixed twice
      tonight elsewhere (get_live_book_lines, build_game_features). Fix:
      batch-load all needed lines once, same pattern as
      get_live_book_lines_batch(). Not urgent today (456s total is still
      fine), but will matter more as recent-form data grows and needs
      re-computation more meaningfully once the season is live.

      
## Known performance issue - RESOLVED (Aug 21, 2026)
- [x] refresh_team_recent_form.py: 307.5s -> 48.9s -> 27.6s across two
      rounds of batching fixes (line lookups, then TeamRecentForm
      existence checks) - both confirmed via direct timing tests before/
      after. Remaining ~27s considered acceptable for a once-daily job;
      not pursued further. Verified output unchanged (Alabama's ATS/O-U/
      SU record identical before and after the rewrite).