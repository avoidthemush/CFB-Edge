# Moneyline Model — Feature Combination Log

Mirrors SPREAD_FEATURE_LOG.md and TOTAL_FEATURE_LOG.md's process and
standards, adapted for Moneyline's real profitability metric: ROI on
actual American odds, NOT win rate vs. a flat breakeven (52.4% only
applies to standard -110 spread/total bets - moneyline odds vary per
bet, so win rate alone cannot indicate profitability).

## Key calibrated values (from OUR OWN data, not literature)
- Margin-to-probability conversion: normal distribution, stdev=15.44
  (calibrated from 2021-2025 FBS games, market_spread_open vs
  actual_spread residuals; mean residual -0.08, confirms spreads are
  unbiased on average). See margin_to_probability.py.
- Devigging: standard proportional method (devig.py), verified sums to
  exactly 100%.

## Real market phenomenon discovered before modeling began
Spread/moneyline DIRECTION disagreement (which team is even favored)
occurs in 4.0% of games, but is NOT random - concentrated almost
entirely in small-spread games (18.3% at |spread|<3, down to 0.1% at
|spread|>=14). Confirmed real market behavior (two independently-priced
markets near a coin-flip game), not a data error. See
DESIGN_DECISIONS.md. Games with |spread|<3 excluded from Type C testing
since favored-team direction is itself ambiguous there.

## Type C: Spread-vs-Moneyline internal consistency (book disagrees with itself)

### Phase 1 test, pct=0.15 threshold - DISCARDED
Validated on 2024: 62.4% win rate, ROI +5.4% (looked strong). Rechecked
on independent split (2023): 61.7% win rate (nearly IDENTICAL), but ROI
-9.1% (LOSING). Critical lesson: near-identical win rates produced
opposite-sign ROI, because ROI depends on WHICH specific bets composed
that win rate (favorite-heavy vs underdog-heavy), not just how many won.
Confirms win-rate-only evaluation would have been dangerously
misleading for Moneyline specifically - ROI must be the deciding
metric for all future Moneyline tests.

**Status: DISCARDED.** Did not proceed to a 2025 test - failed the
second-split check, same standard that discarded Spread's Candidate B.



## Type C systematic search (80 combos, weeks_1_4 + conference_games) - DISCARDED (Aug 2026)

8 combinations showed positive ROI on both 2023 AND 2024 - best was
weeks_1_4 at pct=0.05 (avg ROI +28.4%). All had small samples (20-160
bets) and suspiciously high win rates (65-85%), same red flags as
Spread's early stepwise-search overfitting trap.

Confirmed via extra-year check (2021, 2022): BOTH weeks_1_4 candidates
flip to clearly losing - pct=0.05: -33.6%/-29.7% ROI; pct=0.15:
-13.9%/-19.7% ROI. Two good years followed by two bad years confirms
this was noise, not real signal - 2023/2024 looking good was
coincidental, not persistent.

conference_games candidates not separately re-checked (weeks_1_4 and
conference_games confirmed only 21.1% overlap, genuinely independent
slices) - but given weeks_1_4 collapsed this badly, conference_games
should not be trusted without the same 4-year check before any further
consideration.

**Status: entire Type C systematic search DISCARDED.** No candidate
survived 4-year scrutiny. Consistent with the earlier finding that the
book's spread and moneyline markets, while imperfectly consistent with
each other (4% direction disagreement, mostly near pick'em), do not
show an EXPLOITABLE pattern in that inconsistency - the disagreement
appears to be genuine market noise/independent pricing, not a real,
persistent inefficiency.


## Type B: Market Deviation via rating-gap bucketing - DISCARDED (Aug 2026)

Bucketed by |diff_sp+_rating|, 1-year rolling baseline (mirrors what
worked for Total). Tested 4 percentile thresholds across 3 safe years.
Result: 2/3 years losing at EVERY threshold, win rates 23-32% (clearly
below chance) - not a borderline or thin-sample result, a decisive
failure. DISCARDED, no further tuning warranted on this specific
bucketing dimension.


## Type B: Market Deviation via combined-quality bucketing - DISCARDED (Aug 2026)

Bucketed by combined SP+ rating (both teams' overall quality summed).
Even more decisive failure than the rating-gap version: win rates 7.7%
to 23.3% across all thresholds/years, 2/3 years losing everywhere,
losses far larger than the one profitable year's gains. DISCARDED.

## Type B conclusion for Moneyline (Aug 2026)

Two genuinely different bucketing dimensions tried (rating gap, combined
quality), both mirroring the exact methodology that worked well for
Total. Both failed decisively - not borderline, not "needs more tuning."
Combined with Type C's failure (book's own spread-vs-moneyline
consistency), this represents a real, thorough attempt at market-
anomaly detection for Moneyline, consistent with the project's stated
priority (Type B before Type A). Unlike Total, where Type B succeeded
where Type A failed, Moneyline appears to be the reverse case - or
requires a bucketing dimension not yet tried. Proceeding to Type A
(direct win-probability model) as the next real avenue, having
genuinely exhausted the straightforward Type B attempts first.