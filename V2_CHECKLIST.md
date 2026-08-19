# V2 — Model Build Plan & Completion Review

Companion to V1_CHECKLIST.md. V1 was data-gathering; this covers turning
that data into working Spread/Total/Moneyline predictions. Originally
written as a forward-looking plan (Aug 2026); this version reviews it
against what was ACTUALLY built, correcting assumptions that turned out
wrong along the way - not silently, but explicitly, since several core
assumptions here didn't survive contact with real testing.

## Naming convention (ORIGINAL PLAN - partially superseded)

Original plan: "validation model" (train 2021-2024, test 2025) vs.
"production model" (train 2021-2025). **What actually happened:** this
single train/test split was replaced by a more rigorous 4-fold WALK-
FORWARD validation (train ending 2021/2022/2023/2024, testing
2022/2023/2024/2025 respectively) plus bootstrap resampling (10,000
resamples) for every approved system - a stronger standard than
originally planned, not a shortcut. The validation-model/production-
model DISTINCTION still holds (see train_production_spread.py,
train_production_total.py) - production models are retrained on the
full usable window before going live, validation happens via walk-
forward first.

**Also corrected:** the usable window for anything requiring
market_spread_open/moneyline turned out to be **2021-2025, not
2015-2025** - confirmed via direct data audit (0% opening-line coverage
2015-2020, see V2_SPREAD_FEATURE_LOG.md). The 2015 floor remains real
and useful for non-market features (ratings, stats, coach history).

## 1. Prediction targets - REVISED FROM ORIGINAL PLAN

Original plan assumed:
- Spread: point differential (regression)
- Total: combined points (regression)
- Moneyline: win probability (classification)

**What was ACTUALLY built and approved (Aug 2026):**
- **Spread:** BINARY CLASSIFICATION (does home cover), not regression.
  Two approved systems: General Model (broad), Mid-Season Dog (Focused
  Value tag: week>=5, underdog-only, non-neutral).
- **Total:** NOT a prediction model at all in the end - pure Type B
  market-deviation bucket logic (no ML model, no regression). Four
  approved systems: Pace Deviation, Field Position Deviation, Travel
  Deviation, Wind Deviation, plus a Home Favorite tag on Pace Deviation.
  (Regression WAS tried extensively - Ridge, XGBoost - and failed;
  see V2_TOTAL_FEATURE_LOG.md for the full, honest search history.)
- **Moneyline:** ALSO not a trained model in the end - pure rule logic
  (Unranked Favorite Dog: spread<=10 AND favorite not ranked). A direct
  classifier (Type A) WAS built and tested extensively, but failed;
  the approved system is Type B, market-perception-bias detection.

**Real lesson, confirmed across all three targets:** see
PROJECT_PHILOSOPHY.md - "we are not fortune tellers." Prediction-based
approaches (Type A) worked for Spread but failed for Total and
Moneyline; market-inefficiency detection (Type B) is what actually
found the edge in 2 of 3 targets. This is the single most important
finding of V2, and it directly contradicts this document's original
framing of "three prediction models."

Confirmed: three SEPARATE models/systems built (not a shared
architecture) - this default was never revisited, no clear need arose.

## 2. Train/test split - CONFIRMED, upgraded beyond original plan

Temporal splits used throughout, no random shuffling - confirmed
correct and followed for all three targets. Upgraded from a single
train/test split to full 4-fold walk-forward (see Section 1 above).

## 3. Feature engineering layer - DONE, expanded well beyond original scope

Original plan listed: ratings, advanced stats, returning production,
talent, team ATS, weather, betting line, venue/travel (not yet built),
coaching context (not yet used).

**All built, PLUS substantial additions never in the original plan:**
- Matchup-based features (offense vs. SPECIFIC opponent's defense) -
  the key mid-build realization that offense-vs-offense diffs were
  wrong; see V2_SPREAD_FEATURE_LOG.md.
- Coach quality/upgrade-score/head-to-head (built, used in Spread)
- Returning QB detection (built, used in Spread)
- Pace (plays per drive) - became the core Total signal
- Field position, turnover margin, third-down rate - built via a
  separate EAV-table extraction path, used in Total
- Ranked-opponent flag - became the core Moneyline signal
- Travel distance (current game + prior-game carryover) - built,
  tested for both Spread and Total
- Recent form (last game margin, days of rest)
- Conference-game flag

Both differentials AND raw paired values used throughout, as
anticipated - confirmed the right call, not over-engineering.

## 4. Data leakage risk - RESOLVED APPROACH - CONFIRMED FULLY BUILT

Point-in-time blending approach exactly as planned: one SHARED function
(build_team_features.py / build_game_features.py) used identically for
training-data generation AND live prediction - verified repeatedly via
verify_cache_equivalence.py across every feature addition throughout
V2, never once found to have drifted. This was the single most
important infrastructure decision in the original plan, and it held up
completely under real, extensive use.

2026 live applicability confirmed working: predict_week.py for all
three models runs the identical feature-building code as historical
backtesting, verified against real 2026 Week 1 data multiple times.

## 5. Model type - REVISED FROM ORIGINAL PLAN

Original plan: gradient-boosted trees (XGBoost/LightGBM) as the
starting point. **What actually won:**
- Spread: Logistic Regression (C=0.1, L2)
- Total: No model - bucket/deviation logic. XGBoost WAS tried and
  underperformed a simpler Ridge regression approach, which itself
  then lost to pure Type B bucketing.
- Moneyline: No model - pure rule logic.

Real lesson: model complexity was NOT the bottleneck for any of the
three targets. Simpler approaches consistently won, and the actual
breakthrough in 2 of 3 targets was reframing the QUESTION (market
inefficiency vs. prediction), not upgrading the model type.

## 6. Evaluation approach - CONFIRMED, refined significantly during build

Original plan: compare against closing lines, define a success metric
before evaluating. **What was actually used, refined through real
mistakes:**
- Spread/Total: win rate against a 52.4% breakeven (standard -110
  math), walk-forward + bootstrap, real approved-system bar (3-4/4
  years above breakeven, pooled>=55%, p<0.05, bootstrap>=90%, >=150 bets)
- Moneyline: REAL ROI on actual American odds, NOT win rate - a hard-
  learned lesson (see V2_MONEYLINE_FEATURE_LOG.md) after discovering
  win rate can be actively misleading when payout size varies per bet
  (a near-identical win rate produced opposite-sign ROI in one direct
  test). This is a genuinely important refinement beyond the original
  plan's framing.

## Deferred to live-environment checklist - STILL CORRECTLY DEFERRED

Tracking production model performance/accuracy as the 2026 season
unfolds (rolling record, calibration drift) - still belongs with V3
scheduler/operational work, not yet built. Confirmed still the right
call to defer this.

## Build order - FOLLOWED, with real deviations worth noting

1. Leakage rules - DONE
2. Weekly point-in-time sync layer - DONE
3. Feature engineering (Spread first) - DONE
4. Spread validation + production - DONE (2 approved systems)
5. Total, then Moneyline - DONE (4 systems + 1 tag; 1 system)
   Note: order followed, but each target required GENUINELY DIFFERENT
   search strategies (prediction-based for Spread, market-deviation
   search for Total, extensive Type A/B/C exploration before finding
   Type B success for Moneyline) - not a repeatable template applied
   three times, real, separate investigative work each time.
6. Live tracking / operational work - correctly still not started,
   this is V3's scope.

## SUPERSEDED: "Week 5+ Dog Model" (original Aug 2026 lock)

The original locked Spread system described at the bottom of this
document (week>=5, underdog, confidence>=0.60, using the ORIGINAL
feature set including recruiting) was SUPERSEDED during V2 by two
approved systems using a leaner, better feature set discovered via
systematic category search:

- **General Model** (broad, no restrictions): 55.3% pooled, p=0.0383,
  bootstrap 96.2%
- **Mid-Season Dog** (Focused Value tag, same rules as originally
  described but on the new feature set): 60.8% pooled, p=0.0017,
  bootstrap 99.9% - meaningfully stronger than the original lock

Full history in V2_SPREAD_FEATURE_LOG.md. The original "Week 5+ Dog"
name is retired; "Mid-Season Dog" is the current, correct name for
this system.

## STATUS (Aug 18, 2026): Phase 2 (models) confirmed complete

All three targets have real, approved, production-verified systems:
- **Spread:** 2 systems (General Model, Mid-Season Dog)
- **Total:** 4 systems + 1 tag (Pace/Field Position/Travel/Wind
  Deviation, Home Favorite tag on Pace Deviation)
- **Moneyline:** 1 system (Unranked Favorite Dog)

All 7 systems verified end-to-end against real, live 2026 data across
both tracked books (DraftKings, FanDuel). All findings - approved and
discarded - documented in each target's V2_*_FEATURE_LOG.md, so future
work never blindly re-tests something already ruled out.

**Real, honest gaps carried forward (not hidden):**
- No validated confidence-ranking WITHIN any approved system (tested
  for Moneyline specifically, multiple approaches, none held up -
  systems are used as flat, equal-weight lists, not ranked)
- Total/Moneyline systems are inherently simpler (bucket/rule logic)
  than Spread's trained classifier - this is a finding, not a gap to
  fix reflexively
- Open/live/close line-state tracking still needed for true production
  use (V3 scope, logged in V3_DASHBOARD_PLAN.md)
- Scheduler/automation entirely unbuilt (V3 scope)

**Conclusion: Phase 2 (models) is genuinely, fully ready for Phase 3
(V3) to build on.** Original plan's specific technical assumptions
(regression targets, tree-based models) didn't survive real testing,
but the PROCESS the plan established (temporal splits, shared point-
in-time feature code, defined evaluation bar before declaring success)
held up completely and is exactly what made the real pivots possible
to discover safely.