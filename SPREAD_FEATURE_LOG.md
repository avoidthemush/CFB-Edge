# Spread Model — Feature Combination Log

Running record of every feature-set configuration tested for the Spread
system, so we never re-test blind or lose a result. Updated every time
a new configuration is tried. "Current best" is always the leading
candidate until something beats it on the full standard: 4-fold walk-
forward + bootstrap resampling, both required before promotion.

## Evaluation protocol — TWO PHASES, not one

**Phase 1 (exploration):** internal splits ONLY, 2025 never touched.
Cast a wide net across many combinations here. Use multiple internal
validation years where possible (not just one split) before treating
anything as promising.

**Phase 2 (confirmation):** ONLY for 2-3 finalists that survived Phase 1.
Full 4-fold walk-forward (2022-2025) + bootstrap resampling (10,000
resamples) + leakage sanity check. 2025 is precious - spend this look
deliberately, not on every candidate.

**Already spent tonight (before this protocol was formalized):** original
locked config, Candidates A/B/C, bootstrap on A all touched 2025 during
exploration rather than confirmation. Not fatal, but going forward this
two-phase discipline is mandatory - noted here for honesty, not hidden.

## CURRENT BEST — Candidate A
**Categories:** returning_qb, returning_production, raw_offense_defense_stats
**Walk-forward:** 2022=54.2%, 2023=60.3%, 2024=53.4%, 2025=54.2% — 4/4 above breakeven
**Pooled:** 525/949 = 55.3%, p=0.0383 vs breakeven
**Bootstrap:** 96.2% of resamples profitable, 95% CI [52.2%, 58.4%]
**Status:** Strongest result found to date. Simpler than original locked config
(3 categories vs 9) and outperforms it on every metric.

## History

### 1. Original "Mid-Season Value Dog" (LOCKED, Aug 2026, pre-Candidate-A)
Categories: everything except recruiting_talent (ratings, both matchup
types, returning_qb, returning_production, coach_quality, coach_h2h,
weather, raw_offense_defense_stats)
Walk-forward: 3/4 years above breakeven. Pooled 54.0%, p=0.1463.
Bootstrap: 85.6% of resamples profitable.
Status: SUPERSEDED by Candidate A pending final confirmation - kept as
historical record, not yet formally retired.

### 2. Full feature set (all categories including recruiting)
2/4 years above breakeven. Recruiting confirmed to hurt via ablation.

### 3. L1 vs L2 regularization search (internal split only, train<=2022/test 2023)
L1 @ C=1.0 was the internal-split standout (58.7%, 71/98 features kept)
but never independently confirmed via full walk-forward - deprioritized
in favor of the category-combo search, which found a stronger, simpler
answer (Candidate A) through a more systematic method.

### 4. Category combination search (1,024 combos, internal split only)
Top 15 results ALL included raw_offense_defense_stats - strongest
structural signal found. ratings appeared in ZERO of top 15 (likely
redundant with raw stats, which ratings are computed from).
Candidates B, C tested via full walk-forward as runners-up to A:
- B (returning_production + raw stats only): 3/4 years, pooled 55.2%, p=0.0514
- C (matchups_pass_rush + returning_production + coach_h2h + raw stats): 3/4 years, pooled 53.8%, p=0.2055
Both real, both weaker than A - logged for reference, not pursued further
unless A is later beaten.

## Next planned step
Forward selection FROM Candidate A's 3-category base: test adding each
remaining category (ratings, recruiting_talent, matchups_pass_rush,
matchups_trenches, coach_quality, coach_h2h, weather) ONE AT A TIME on
top of the proven base, via full walk-forward. Keep any addition that
improves on Candidate A's pooled win rate AND bootstrap %; discard
additions that don't, even if they look neutral - simpler is preferred
when performance is equal.

## CORRECTION: usable historical window for open-line-dependent testing (Aug 2026)

Discovered while building Phase 1 exploration: market_spread_open
coverage is 0% for 2015-2020 (not just 2015-2018 as first documented -
2019 and 2020 both fully lack it too, confirmed via
check_phase1_split_years.py). Real usable window starts at 2021, not
2019. This means the "two-phase, protect 2023-2025" design has only
2 clean years (2021, 2022) available for Phase 1 exploration - not
enough for a robust multi-split internal search as originally planned.

## Stepwise individual-feature search - DISCARDED (Aug 2026)

Ran automated forward/backward stepwise search across ~85 individual
features (not just categories), starting from Candidate A's base.
Validated against 2024: converged to 59.80% (28 features, including
away_recruiting_points and isolated precip_prob - both suspicious given
prior findings). Re-ran identical algorithm validated against 2023:
converged to 68.45% (34 features) with almost NO overlap in selected
features vs. the 2024 run.

Conclusion: two runs of the same method, same base, same goal, produced
wildly different "best" feature sets and increasingly implausible win
rates - the definitive signature of overfitting, not real signal. Our
sample size (~200-230 confident bets per single validation year) cannot
support exhaustive individual-feature search; there are more possible
combinations than games to distinguish between them.

DECISION: both stepwise results discarded, never taken to Phase 2/2025.
Candidate A (returning_qb + returning_production + raw_offense_defense_
stats, category-level, category-search-derived) remains the validated
best - this exercise strengthens confidence in it by comparison, since
Candidate A survived a full walk-forward + bootstrap under a more
conservative search method, while stepwise search demonstrably cannot
be trusted at our current data scale.

Future consideration: individual-feature stepwise search could become
viable again once we have meaningfully more historical seasons with
real market_spread_open coverage (currently just 2021-2025, 5 years) -
revisit if/when that changes.