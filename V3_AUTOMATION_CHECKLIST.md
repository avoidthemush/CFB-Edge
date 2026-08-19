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