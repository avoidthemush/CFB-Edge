# Total Model — Feature Combination Log

Mirrors SPREAD_FEATURE_LOG.md's process and standards. Same approved-
system bar: 3/4 walk-forward years above breakeven, pooled >=55%,
p<0.05, bootstrap >=90% profitable, >=150 pooled bets.

## Standard evaluation protocol
Same as Spread: Phase 1 (train 2021-2023, validate 2024, plus a second
split validating 2023, 2025 untouched) -> Phase 2 (full 4-fold walk-
forward 2022-2025 + bootstrap) for anything that survives Phase 1.

## Discarded

### Classifier approach (binary over/under, combined/additive features)
Phase 1 only, never reached Phase 2: coefficients showed offensive
efficiency (success rate, explosiveness) counterintuitively favoring
UNDER - confirmed stable across 2 splits (13/17 features agreed on
direction) but the DIRECTION itself was likely a classifier/
multicollinearity artifact, not real. Win rate weak (46-49%) at every
regularization strength tested. Superseded by regression approach.

### Regression approach (predict actual_total directly, gap vs market_total_open)
Coefficients corrected to sensible directions once switched from
classifier to regression (efficiency now correctly favors OVER,
pace/wind correct in both approaches). Phase 1 showed real promise
(train/val MAE gap only 0.30-0.35, some thresholds cleared breakeven in
both internal splits). FAILED Phase 2: 2025 (untouched year) below
breakeven at every gap threshold tested (2/3/5/7). Pooled results never
cleared p<0.05 or 90% bootstrap at any threshold. Best result: Gap>=7,
53.4% pooled, p=0.3419, bootstrap 69.5%.

**Conclusion:** combined/additive regression is the right STRUCTURAL
approach (real, stable, football-sensible coefficients) but current
feature set + simple Ridge regression insufficient for a real edge.
Same lesson as Spread's early attempts - structure alone isn't enough,
need better features or a genuinely different approach.

## Queued for Total specifically
- Rolling Over/Under streak (queued alongside Spread's ATS streak - same
  build, parallel feature)
- Test keeping some features as separate home/away pairs rather than
  always combined/summed - "combined" framing may be losing information
  a differential or paired approach would keep
- Test tree-based (XGBoost) regression instead of linear Ridge - Total's
  relationship between combined pace/efficiency and actual scoring may
  be more non-linear than Spread's cover/no-cover question
- Higher-order interaction terms (e.g. pace x efficiency, not just both summed)

## Matchup-based approach - investigation of negative coefficient (Aug 2026)

combined_matchup_scoring_potential showed negative coefficient (favors
UNDER) despite strong Phase 1 win rates. Investigated directly:
- Raw correlation with actual_total: +0.021 (positive, as expected)
- High vs low matchup potential groups: 54.6 vs 53.6 avg total (positive, as expected)
- Correlation with margin_abs: -0.001 (garbage-time/blowout theory RULED OUT)
- Correlation with combined_pace: 0.335 (real multicollinearity confirmed)

Conclusion: negative coefficient is a genuine multicollinearity artifact
(matchup potential overlaps with pace), NOT evidence of a real inverse
relationship. Raw signal confirmed positive and real. Cleared to proceed
to Phase 2 confirmation.

## Matchup-based approach - FAILED Phase 2 (Aug 2026)

Full 4-fold walk-forward: 2022=49-51% (below breakeven all thresholds),
2023=52.5-56.7% (strong), 2024=52.8-55.4% (strong), 2025=48.2-50.9%
(below breakeven all thresholds). Notably 2022 was NEVER part of Phase 1
- this is 2 genuinely independent years failing, not just the one sealed
year - a stronger negative signal than a single bad year.

Pooled: never clears 52.5% at any threshold, p-values 0.49-0.71 (nowhere
near significant), bootstrap 29-51% profitable. DISCARDED.

Two Total approaches now failed the same fundamental way (strong on 2
years, weak on 2 others): purely additive, and matchup-adjusted. Both
had sound underlying logic (confirmed via direct investigation, not just
assumed) but neither found a reliable, sample-stable edge. Points to
either (a) genuinely no exploitable Total edge exists with current
features/simple linear models, or (b) a fundamentally different
approach/richer feature set is needed - not more tweaking of this
structure.

## Tree-based (XGBoost) approach - NOT ADVANCED TO PHASE 2 (Aug 2026)

Full unconstrained feature set (98 raw columns, no hand-combining).
Overfitting gap notably worse than either linear attempt (1.58-2.31 vs
0.30-0.35) - real concern given tree models' capacity to memorize with
this many features. Win rates weaker/less consistent than the matchup-
based Ridge approach that already failed Phase 2. Feature importances
show no standout signal (tight 0.009-0.014 band across top 15) -
consistent with "no strong pattern for a tree to find" rather than a
subtle non-linear pattern being captured.

Given weaker Phase 1 signal AND worse overfitting than an approach that
already failed the real test, did not spend a Phase 2 look at 2025 on
this - not defensible given what we already know.

## Status: three structurally different approaches tried, none found a
real, sample-stable Total edge (additive linear, matchup-adjusted
linear, unconstrained tree-based). Per user's standing instruction,
stepping back to reassess rather than continue iterating blindly.

## Decomposed home/away approach - NOT ADVANCED (Aug 2026)

Predicted home_points and away_points separately (respecting the exact
Total=home+away identity), with explicit pace x efficiency interaction
term. Weaker than the already-failed matchup-based approach at every
comparable threshold - especially split 2 (Gap>=5 dropped to 51.0% vs
matchup approach's 56.5%). Mathematically cleaner framing did not
translate to better results; likely because separate home/away errors
compound rather than cancel. Not advanced to Phase 2.

## Rolling 1-year training window - CLOSEST RESULT, still under the bar (Aug 2026)

Motivated by a real, confirmed finding: corr(combined_pace, actual_total)
declines monotonically 2022->2025 (0.194 -> 0.169 -> 0.063 -> 0.021),
suggesting the true relationship may be drifting, diluted by training on
multiple years equally. Tested training on ONLY the immediately-prior
year (not the full expanding history).

3 of 4 rolling folds cleared breakeven (only 2021->2022 failed - the
single most stale fold, consistent with the drift theory). Pooled best
result (Gap>=5): 53.7%, p=0.1703, bootstrap 84.0% profitable, 95% CI
[51.1%, 56.3%].

STATUS: closest result found across all Total approaches tonight (6
structural attempts total), but does NOT clear the approved bar (needs
>=55% pooled, p<0.05, >=90% bootstrap). Genuinely promising direction -
worth revisiting with a larger recent-data window (e.g. rolling 2-year
instead of strict 1-year) or combined with pace's declining-correlation
insight in a more sophisticated way (e.g. weighting games within the
training set by recency, not just cutting off older years entirely).
NOT approved. Under the bar, not discarded.

## Market Deviation approach - cleared ALL THREE safe years (Aug 2026)

Fundamentally different signal type: not predicting the total ourselves,
but detecting when the MARKET's own posted total looks mispriced
relative to recent (prior-year) games with similar combined pace. Bet
OVER when market total is unusually LOW for that pace level, UNDER when
unusually HIGH.

First Total approach to clear breakeven in ALL THREE safe years,
including 2022 (which broke every other attempt tonight):
2022=52.6%, 2023=56.5%, 2024=58.4% - consistent upward trend, not
scattered. This has earned a real Phase 2 test on 2025.

## APPROVED SYSTEMS — under category "Market Deviation Systems"

Both systems below share the same METHODOLOGY (Type B: detect when the
market's posted total is an outlier relative to recent comparable
games, bucketed by a specific factor) but are INDEPENDENT systems, not
one shared prediction with different filters (unlike Spread's General
Model / Mid-Season Dog relationship). Each has its own bucketing logic
and stands alone.

### Tag: "Pace Deviation" (formerly "Market Deviation")
Buckets by combined_pace. Pooled 55.0% (936 bets), p=0.0577, bootstrap
95.0%. 4/4 years above breakeven.

### Tag: "Field Position Deviation"
Buckets by combined offensive field-position value. Pooled 57.3%
(475 bets), p=0.0188, bootstrap 98.6%. 3/4 years above breakeven
(2025 essentially neutral at 50.4%, not a collapse).

Both tags can fire independently on the same game - a game could
qualify for Pace Deviation, Field Position Deviation, both, or neither.

## Field Position Deviation - baseline robustness check (Aug 2026)

User raised a fair concern: is the approved 1-prior-year baseline
(~78 games/bucket) too thin/fragile? Tested 1, 2, and 3-year baselines.
Core pattern holds at all three (2023/2024 strong, 2025 neutral, never
flips negative) - not a pure fluke. BUT significance/pooled rate
actually WORSENS with more years (p=0.017 -> 0.094 -> 0.069) despite
larger, more stable buckets (77 -> 154 -> 233 games/bucket) - opposite
of what pure sample-size noise would predict.

Likely explanation: mirrors the pace-correlation drift already found
for Pace Deviation - if the underlying market inefficiency is itself
recent/evolving, older baseline years reflect a stale market and
actively dilute the signal. 1-year baseline appears to be the correct
design choice, not an under-scrutinized shortcut - confirmed via direct
testing, not assumed. Remaining unchanged as approved.

## APPROVED SYSTEM #3

### Travel Deviation
Buckets by combined travel distance (home + away). Independence
confirmed (all correlations with existing signals < 0.05). 3/4 years
(2025 neutral, 51.2%, not negative). Pooled 57.4% (319 bets), p=0.0425,
bootstrap 96.2%.

## APPROVED SYSTEM #4

### Wind Deviation
Buckets by wind_mph, filtered to home-favorite games only. Independence
confirmed. 3/4 years (2025 neutral, 49.3%). Pooled 58.6% (292 bets),
p=0.0200, bootstrap 98.2%.

## Pattern worth flagging: all 4 Total systems share the same shape

Pace, Field Position, Travel, and Wind Deviation ALL show: strong
2022-2024, essentially neutral (not negative) 2025. Each passed
independence checks individually, but the shared 2025 softening across
ALL FOUR raises a real question worth investigating: is this 4
independently real signals, or does something systemic about 2025
itself (market behavior shift, data characteristic) dampen multiple
signals simultaneously? Worth checking directly before adding a 5th
system to this pattern uncritically - see next check.