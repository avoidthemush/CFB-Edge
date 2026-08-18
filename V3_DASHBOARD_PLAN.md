# V3 — Dashboard & Productionization Plan

Placeholder doc, created during V2 model work (Aug 2026) to capture
architecture decisions made while thinking ahead, so they're not lost
before V3 actually starts.

## Confirmed direction
- Scheduler (V1 Section D) will eventually run BOTH data syncs AND
  model inference each week, not just data syncs.
- Predictions must be persisted, not just generated in-memory - needed
  for a real dashboard and for live performance tracking.

## Proposed new tables (not yet built)
- `model_predictions` - one row per game per model run. Game identity,
  market context at prediction time (opening AND current line - lines
  move), model output (predicted margin/probability), which angle it
  qualifies under (if any), qualifies_for_bet flag, model version/
  timestamp, actual outcome once known (for grading).
- `edge_definitions` - reference table for each named angle/strategy:
  name, description, the actual rule, historical validated performance
  (win rate, sample size, date range). Dashboard shows this alongside
  live picks for context/trust.

## Terminology decision
"Subset edge" replaced with industry-standard term "SYSTEM" (matches
real betting-industry convention, e.g. Action Network - a defined,
situational betting rule validated to produce edge under specific
conditions).

## Named systems so far
- Week 5+ Dog -> FINAL NAME: "Mid-Season Value Dog" (display name) /
  `mid_season_value_dog` (internal code, matching validation_model/
  production_model naming convention)

## Open questions for when V3 actually starts
- How does bet tracking (actual stakes placed, if any) relate to
  model_predictions - same table or separate?
- Does edge_definitions need versioning too (an angle's rules could be
  refined over time)?
- Dashboard auth/access - single user or multi-user from the start?

## Open/Live/Close line tracking (raised Aug 2026, deferred to V3)

Confirmed design (user-specified): three distinct line states per game/book:
- **Opening line**: earliest timestamped snapshot for a game
- **Live line**: most recent snapshot where pulled_at < kickoff time (updates
  continuously pre-game)
- **Closing line**: once kickoff occurs, the last pre-kickoff snapshot
  becomes permanent - no longer needs "live" updates after that point

Current state (Aug 2026): get_live_book_lines() only has a cruder
two-state approximation (earliest snapshot vs. most-recent snapshot) -
does NOT check kickoff time, so a post-kickoff poll could incorrectly
be treated as "current" for a game that's already started.

**Real dependency identified:** closing line QUALITY depends on
scheduler polling FREQUENCY near kickoff. Flat/daily polling would give
a stale close. Scheduler should poll more frequently as kickoff
approaches (e.g. daily days out, every 15-30 min in the final hour+)
rather than a constant interval - this is a scheduler design
requirement, not just a query-logic change.

**Confirmed via research:** The Odds API's dedicated Historical Odds
endpoint costs 10x normal credits (10 per region/market vs 1) and
requires a paid plan - our existing approach (polling the cheap /odds
endpoint ourselves and storing snapshots) is the right, cost-effective
way to build this ourselves rather than using their historical endpoint.

**Action items for V3:**
1. Add kickoff-time comparison to line-snapshot logic (open/live/close split)
2. Design scheduler polling frequency to intensify near kickoff
3. Decide whether "close" gets a dedicated DB flag/table, or is derived
   on-the-fly from existing odds_snapshots + game start_time

   ## Season Architecture: Pre-populate, Layer, Refresh (confirmed Aug 2026)

Core principle: build the ENTIRE season's skeleton as soon as the
schedule is known (months ahead of kickoff), then let independent data
layers fill in and refresh on their own natural cadence - rather than
treating "generate this week's predictions" as one big, from-scratch
action each time.

### Layer 1: Full season schedule (pre-populate immediately)
sync_games.py already pulls the full season's schedule when it runs -
confirmed this is why 211 Week 1 2026 games already existed in the DB
months before kickoff. No new work needed here; just formalizing that
this SHOULD run as early as CFBD publishes the schedule, not incrementally.

### Layer 2: Static, fully-determined-at-schedule-time data
Fields that depend ONLY on (team, venue) and never change once the
schedule is set - compute immediately, don't wait for game week:
- Venue, location, dome/outdoor (already static via existing sync)
- Travel distance (home_travel_distance/away_travel_distance - already
  computable the moment a game+venue exists, per travel_distance.py)
- Conference game flag (already static via teams.conference)
- Neutral site flag (already part of the game record)

### Layer 3: Weekly-refreshing data (existing cadence, already correct)
Team stats, ratings, coach tendencies, returning production, box-score
stats (turnovers, third-down) - these update as the season progresses,
via the existing sync_weekly_stats.py / sync_ratings.py / etc.
architecture. No design change needed - this layer already works
correctly, just needs the SCHEDULER (still unbuilt) to actually run it
automatically on a weekly cycle instead of manually.

### Layer 4: Continuously-evolving line data (NEW - needs the
open/live/close design already logged above in this doc)
Lines can post anywhere from weeks out to hours before kickoff, and
keep moving until kickoff. This layer is genuinely different from
Layers 2-3: it doesn't have a fixed refresh cadence, it needs
POLLING FREQUENCY THAT INCREASES as kickoff approaches (see open/live/
close section above). This is where the scheduler design work
concentrates - not just "run weekly," but "poll more as game day nears."

### Layer 5: Predictions (derived, not stored-then-stale)
Once Layers 2-4 exist for a game, predictions should reflect whatever
the CURRENT state of the data is - re-run automatically whenever Layer
3 (weekly stats) or Layer 4 (lines) meaningfully update for a game, not
just once per week on a fixed schedule. model_predictions already has
the right shape for this (upsert by game+system+book, not append-only),
confirmed working correctly in tonight's testing.

### Why this matters for the scheduler design (V3, not yet built)
The scheduler isn't one job - it's at least three jobs with different
cadences:
1. Full-season schedule sync - runs once, early, before the season starts
2. Weekly stats/ratings sync - runs weekly during the season
3. Odds polling - runs frequently, INCREASING in frequency near each
   game's kickoff (not a flat interval)
Predictions (predict_week.py equivalents) should be triggered by #2 and
#3 completing, not run independently on their own schedule.

### Known bug classes to design around (learned Aug 2026, real, not hypothetical)
- FBS-vs-FBS filtering must be explicit at the QUERY level for any live
  prediction, not assumed - confirmed real bug (FCS teams appeared in
  live Total picks) when this was missed.
- New betting systems MUST be added to seed_betting_systems.py at
  approval time, or their predictions display correctly but silently
  fail to persist - confirmed real bug (Travel/Wind/Home-Favorite-tag
  picks were computed and shown but never written to the DB for one
  full run before the seed script was updated).
- Live line lookups must use OUR OWN polled DK/FanDuel data
  (get_live_book_lines), never fall back to CFBD/Bovada for live/
  upcoming games - confirmed real bug (stale Bovada-sourced total via
  CFBD was used instead of current DK/FanDuel data, a real 2-point gap
  on a real game).
- Any live-prediction script must use FeatureCache, never call
  build_game_features() in a bare per-game loop - confirmed real bug
  (45+ minute runtime from rebuilding the coach H2H index from scratch
  per game, fixed to ~2 minutes).


## Pre-rollout checklist (add before V3 launch)
- [ ] Final V2 summary doc: consolidated overview of all three models
      (Spread: General Model + Mid-Season Dog; Total: Pace/Field
      Position/Travel/Wind Deviation + Home Favorite tag; Moneyline:
      Unranked Favorite Dog) - performance stats, known limitations,
      and links to each full feature log. Written once, right before
      rollout, not maintained continuously during V3 build.