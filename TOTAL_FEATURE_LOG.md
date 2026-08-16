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