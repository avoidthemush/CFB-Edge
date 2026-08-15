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