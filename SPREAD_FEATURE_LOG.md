# Spread Model — Feature Combination Log

Running record of every feature-set configuration tested for the Spread
system, so we never re-test blind or lose a result. Updated every time
a new configuration is tried. "Current best" is always the leading
candidate until something beats it on the full standard: 4-fold walk-
forward + bootstrap resampling, both required before promotion.

## Standard evaluation protocol (applies to every entry below)
- 4-fold walk-forward: train 2015-2021/test 2022, ...train 2015-2024/test 2025
- Confidence >= 0.60 threshold always applied as the base filter
- Bootstrap: 10,000 resamples, report % of resamples above 52.4% breakeven

## Two-phase testing process (standing process, formalized Aug 2026)

**Phase 1 (exploration):** internal splits ONLY - train 2021-2023,
validate 2024. 2025 never touched during exploration. Cast a wide net
here, iterate freely.

**Phase 2 (confirmation):** ONLY for candidates that survive Phase 1.
Full 4-fold walk-forward (2022-2025) + bootstrap resampling (10,000
resamples) + leakage sanity check. 2025 is precious - spend this look
deliberately, not on every candidate.

**Note on years 2015-2020:** confirmed 0% market_spread_open coverage
across the board (CFBD's dominant provider for those years - consensus/
teamrankings - never carried opening lines). Real usable window for
anything requiring an opening line is 2021-2025, not 2015-2025. The
2015-2020 backfill remains valuable for other model needs (ratings,
stats, weekly point-in-time data) but contributes near-zero to Spread
specifically.

## Approved Systems — minimum bar (Aug 2026, revised)

A system is added to "Approved" only if ALL of the following hold:
- 3/4 walk-forward years above 52.4% breakeven
- POOLED WIN RATE >= 55% (not just breakeven - 55% ATS is the standard
  industry threshold for a genuinely sustainable edge, ~5% ROI per bet
  at -110; anything 52.4-55% is a real but thin margin, too easily
  swallowed by variance to call "respectably profitable")
- Pooled win rate significant vs breakeven, p < 0.05
- Bootstrap: >=90% of resamples profitable
- >=150 pooled bets across the 4-fold walk-forward

Systems that are real/sensible but don't clear this bar stay documented
in "Under the bar" - not deleted, just not promoted.

## APPROVED SYSTEMS (restructured, Aug 2026)

### General Model
Broad, always-on prediction. Runs on every game, every week, no
situational restrictions (no week/underdog/site filter). Confidence>=0.60
is the only rule.

**Features:** returning_qb + returning_production + raw_offense_defense_stats
(no recruiting - ablation-confirmed to hurt)

**Performance:** 4/4 walk-forward years above breakeven (2022=54.2%,
2023=60.3%, 2024=53.4%, 2025=54.2%), pooled 55.3% (949 bets), p=0.0383,
bootstrap 96.2% of resamples profitable.

This is the production model that predict_week.py runs on every game.
Focused Value systems (below) are the SAME trained model with additional
situational filters applied at prediction time - not separate models.

### Focused Value (category - situational systems, each individually tagged)

Narrower, higher-conviction angles layered on top of General Model's
same underlying prediction. When a new situational rule clears the
approved bar, it gets added here as a new tag - never a new model.

---

**Tag: "Mid-Season Dog"** ✅ APPROVED

Rule: week >= 5, underdog-only, non-neutral-site, confidence >= 0.60
(applied on top of General Model's prediction)

**Performance:** 3/4 years above breakeven (2022=65.8%, 2023=64.4%,
2024=57.1%, 2025=50.0% exactly at breakeven, n=46 - thinnest sample,
flagged for live 2026 monitoring), pooled 60.8% (316 bets), p=0.0017,
bootstrap 99.9% of resamples profitable. Strongest significance found
of any system tested.

**Naming note:** this tag was originally tested under the name
"Mid-Season Value Dog" using the ORIGINAL locked feature set (everything
except recruiting) - that version did NOT clear the approved bar
(pooled 54.0%, p=0.1463 - fails significance). The APPROVED version
uses General Model's leaner feature set instead, which does clear the
bar. Same conceptual angle (week>=5, underdog, non-neutral), different
underlying model. Only the General-Model-based version above is approved
for production use.

---

*(No other tags currently approved.)*

## Under the bar (real, documented, historical reference only)

- **Original "Mid-Season Value Dog"** (pre-Candidate-A feature set) -
  3/4 years, pooled 54.0% (1184 bets), p=0.1463. Fails significance bar.
  Superseded by the "Mid-Season Dog" tag above.

## Discarded (tested, did not clear the bar, one-line log)

- Full feature set (incl. recruiting): 2/4 years, recruiting hurts.
- Candidate B (returning_qb + returning_production + coach_quality +
  weather + recent_form): survived 2 internal checks, FAILED Phase 2 -
  2025 came in at 46.5%, pooled 53.9%, p=0.2529, bootstrap only 76.4%.
- L1 vs L2 regularization search (internal split only): never independently
  confirmed, superseded by category-level search methodology.
- Category combination search (1,024 combos, internal split): top 15
  all included raw_offense_defense_stats (real structural signal,
  already captured in General Model); ratings appeared in zero of top
  15 (redundant with raw stats).
- Stepwise individual-feature search (2024-val AND 2023-val runs):
  proven to overfit - two runs on different validation years produced
  almost no overlapping selected features and increasingly implausible
  win rates (59.80% then 68.45%). Both discarded.
- Variable-size category search, first pass (15-bet floor): let tiny-
  sample noise dominate (top "result" was 77% on 22 bets) - discarded,
  not real.
- Variable-size category search, second pass (100-bet floor): Candidate
  A/General Model reappeared unprompted as best 3-category combo (good
  consistency check). Sizes 4-6 showed 56-58% results but at smaller
  samples (100-131 bets) and several reintroduced recruiting_talent
  (already proven harmful) - not trusted.
- 21 individual category pairs added to General Model's base: 0/21 beat
  baseline.
- Coach experience gap as standalone rule (not model-based): all
  thresholds tested (3/5/8 years) below breakeven, no trend - discarded.
- Large underdog segment (spread_open >= 14, General Model + confidence
  >=0.60 + underdog): 56.8% pooled but only 132 bets, p=0.1765 (not
  significant), bootstrap 83.6% (below 90% floor), 2025 exactly at
  breakeven with only 10 bets - too thin to trust. Real hypothesis
  (backed by documented industry research on "double-digit dogs"),
  insufficient sample with current data - revisit as more years accumulate.

## Queued, not yet tested

- Rolling in-season ATS streaks - requires a genuinely NEW feature
  (cumulative ATS record computed week-by-week from cfbd_betting_lines +
  games, not just the season-end team_ats table we already have).
- "Tough loss" recent-form segment (large negative last_game_margin) as
  a standalone tag - feature exists (recent_form.py), never tested as
  its own angle.
- Travel distance / short-week-after-long-travel fatigue - feature
  built (travel_distance.py), verified (Alabama->USC = 1,763 miles,
  correct), but never wired into build_game_features.py or tested.

## Production status

Production model retrained on General Model's feature set (2021-2025,
3,869 games, 38 features) - see app/models_ml/spread/train_production_spread.py.
predict_week.py reports BOTH General Model picks (every game) and
Focused Value / "Mid-Season Dog" tag picks (the situational subset) per
game, from the same underlying prediction. Verified end-to-end against
real 2026 Week 1 data (Aug 15, 2026) - 51/211 games had posted lines,
7 General Model picks generated, 0 Mid-Season Dog picks (correctly
zero - week>=5 requirement not met in week 1, by design).

Known caveat: General Model has no week restriction and technically
produces output for weeks 1-4, but calibration testing (see archived
ats_calibration_check.py results) proved confidence is NOT reliable in
that window - some buckets performed below a coin flip. Early-week
General Model picks should not be treated as trustworthy until this is
resolved (queued: rolling ATS/other early-season signal work above).