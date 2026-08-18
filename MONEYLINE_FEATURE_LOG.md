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