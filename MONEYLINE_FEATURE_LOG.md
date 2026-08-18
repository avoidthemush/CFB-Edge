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


## Type A: direct "home_won" classifier - genuine calibration, but EV betting fails (Aug 2026)

Classifier (same proven feature categories as Spread's General Model,
new target = home_won): 68.1% overall accuracy, GENUINELY well-
calibrated (predicted-probability buckets closely match actual outcome
rates, e.g. predicted 70-80% -> actual 75.7%). This is real, verified
skill, not a false positive.

Edge-gap betting (disagree with market): losing at every threshold
except the highest (edge>=0.15, barely +0.8% ROI, thin sample).

EV-based betting (mathematically correct framing: prob x payout vs
stake): performed WORSE (-12.9% to -15.2% ROI at every threshold).
Diagnosed directly: EV-qualifying bets are overwhelmingly longshots
(91.1% of away-side qualifiers, 69.2% of home-side qualifiers are
underdogs; avg qualifying away odds +430 vs overall average +32). Large
payout multipliers amplify small, honest calibration imprecision into
apparently-huge-but-fake EV on longshots specifically - a well-known
sports betting trap (the model is calibrated in AGGREGATE across a
bucket, not necessarily PRECISE on any single game, and high payouts
punish imprecision severely).

Real, useful finding, not a dead end: this model likely has genuine
value on games where it AGREES closely with the market (both saying
~similar probability) but ALSO where the market's price offers a
built-in cushion (moderate favorites/dogs, not extreme longshots).
Underdog longshot bets specifically should be treated with far more
caution or excluded until we can either (a) improve model precision
specifically at the tails, or (b) build a confidence/uncertainty
measure per prediction, not just a point probability.


## Type A: narrow-odds-range EV classifier - FAILED Phase 2 (Aug 2026)

Two internal splits gave conflicting signals: 2024 validation showed an
erratic, sign-flipping pattern (real warning sign); 2023 recheck showed
a clean, monotonic profitable pattern (real encouragement) - earned a
Phase 2 test on that basis.

Full walk-forward (EV>=0.08, odds -200 to +150): 2022=-8.1%, 2023=+7.0%,
2024=-0.3%, 2025=-0.4%. Pooled: 282/559 = 50.4% win rate, ROI=-0.4%.
3/4 years losing; the one profitable year is the SAME year that already
looked good in the recheck, not new independent confirmation.

Pooled win rate (50.4%) on near-zero average odds is essentially what a
coin flip would produce - consistent with the model's GENUINE
calibration (confirmed earlier) landing close to the market's own fair
assessment, not finding a real, exploitable edge. The market is pricing
these games about as accurately as our model does.

**Status: DISCARDED.** Type A (direct win-probability classifier)
exhausted for Moneyline with this feature set/model, after genuine,
multi-stage testing (edge-gap, raw EV, capped EV, narrow EV, second-
split recheck, full walk-forward).


## Overall Moneyline status (Aug 2026)

Both Type B (2 bucketing dimensions: rating gap, combined quality) and
Type A (direct classifier: edge-gap, EV, capped EV, narrow EV, 2-split
+ full walk-forward) tested with real rigor - matching the standard
applied to Spread and Total. No approved system found.

Real, useful findings even without an approved system:
- Moneyline market appears MORE efficiently priced than Total's market
  specifically - consistent with moneyline being the simplest, most
  heavily-scrutinized number on the board (just "who wins"), while
  Total requires synthesizing more inputs (pace, weather, matchup),
  leaving more room for the structural blind spots we found there.
- Our classifier IS genuinely well-calibrated (verified directly) - the
  problem isn't bad predictions, it's that the market is ALSO
  well-calibrated on moneyline specifically, leaving little room for
  our informational edge to translate into profit once real vig and
  payout structure are accounted for.
- Confirmed a real, general lesson for all future modeling: win rate is
  actively MISLEADING for uneven-payout bets (moneyline) - a near-
  identical win rate produced opposite-sign ROI in one direct
  comparison. ROI must be the deciding metric, never win rate alone,
  for any moneyline-style evaluation.

**No approved Moneyline system at this time.** Genuinely revisitable
later (per user's stated plan to eventually revisit all three models
once more data accumulates) - not a permanent dead end, an honest
"insufficient signal with current data/methods."


## Favorite-Longshot Bias (FLB) research-driven test (Aug 2026)

Grounded in real, peer-reviewed research (Berkowitz et al., confirmed
FLB specifically in college football/basketball moneylines). Blind
underdog-betting-by-spread-bucket test CONFIRMED the bias cleanly and
decisively at scale (n=3,669): monotonic ROI decay from +1.5% (0-3 pt
dogs) down to -33.0% (21+ pt dogs). This is real, structural market
behavior, strongly confirmed - not noise.

However, the one profitable bucket (slight dogs, 0-3) does NOT hold up
as a standalone bet: 3/5 years losing, no trend (+16.6%/-5.6%/-1.7%/
+13.6%/-15.6%). Combining with our own model's independent agreement
made results WORSE, not better - and critically, 2025 (the one
genuinely fresh year) failed at EVERY confidence threshold tested
(-22.6% to -17.4%), while pooled numbers only looked better because
2023/2024 improved as the threshold tightened - the classic overfitting
signature (tightening helps only in years already seen).

**Status: DISCARDED as a standalone or model-combined system.**

**Real, valuable finding for the record:** the favorite-longshot bias
is confirmed, real, and strong in our own CFB data - useful as a
STRUCTURAL constraint/sanity check for the whole project (e.g. never
build a system that leans toward big underdogs without a very strong,
independently-verified reason), even though it didn't yield a directly
tradeable standalone system in the narrow zone where the bias theoretically
should have been weakest.



## Home/Away FLB split - inconclusive, re-slicing broke the clean pattern (Aug 2026)

Splitting the clean pooled FLB staircase by home/away dog status
produced noisy, non-monotonic results in both splits (home dogs:
+2.4%/+1.1%/-6.9%/+18.2%/-30.0%/+1.3%; away dogs similarly erratic).
Confirms the AGGREGATE pooled pattern is real, but doesn't survive
being re-sliced into smaller home/away buckets - sample sizes too thin
per cell to trust individually.

## Situational systems (travel/letdown, user-suggested) - Aug 2026

"Far travel alone (>500mi)" for home dogs: 3/5 years profitable
including 2025 (+0.9%, modest but real), pooled +3.1%. Most credible
finding of tonight's situational tests, but not a clean trend - close
to the bar, doesn't clearly clear it. NOT approved, logged as a
genuine near-miss worth revisiting with more data.

"Combo: far travel + big prior win": pooled +6.2% looked strong, but
driven almost entirely by 2021 (+60.4% on 22 bets) - 3/5 years actually
losing including 2025 (-18.9%). Classic small-sample noise pattern
already seen twice tonight (Total's Candidate B, Moneyline's weeks_1_4).
DISCARDED.


## APPROVED SYSTEM

### Unranked Favorite Dog
Bets the underdog's moneyline when: (1) spread <= 10 (FLB sweet spot,
confirmed via research + our own data that big dogs are structurally
bad value), AND (2) the favorite is NOT a ranked (AP Top 25) team.

**Mechanism:** public/market perception bias toward "brand name" ranked
teams appears to push their moneyline price further from fair than an
equally-strong-but-unranked favorite gets - the underdog against an
unranked favorite is comparatively undervalued.

**Performance:** 5/5 years profitable, BOTH directions confirmed
(unranked-favorite dogs profitable every year 2021-2025: +14.4%, +3.8%,
+3.8%, +7.6%, +2.8%; ranked-favorite dogs LOSING every year: -0.8% to
-20.5%, confirming the mechanism symmetrically). Pooled: 1,494 bets,
+$9,403 profit, ROI +6.3%. Bootstrap: 96.6% of resamples profitable,
95% CI [-0.5%, +13.1%].

**Status: APPROVED.** Found via genuine, extensive search (Type A, Type
B x2, Type C, FLB research, home/away split, situational systems, then
this) - a real, hard-won first Moneyline system, not a shortcut.


## Confidence ranking within Unranked Favorite Dog - not yet found (Aug 2026)

User asked for a way to rank the ~20 weekly qualifying games rather
than bet all of them. Tested two market-based ranking signals:
- Spread size within the 0-10 range: no clean trend (-6.9%/+5.4%/
  +10.0%/+1.8%/+17.1% across sub-buckets) - discarded.
- Moneyline-vs-spread gap size: also no clean trend (+8.1%/+12.2%/
  -9.0%/-4.2%) - discarded.

Honest conclusion: no validated within-system confidence ranking found
yet. System remains approved and usable AS A WHOLE (bet all qualifying
games), not yet safely narrowable to "the best few" without risking
manufacturing a false pattern from further slicing. If fewer, higher-
conviction bets are wanted, the responsible path is tightening the
QUALIFICATION rule itself (e.g. stricter spread cap) and re-validating
with full rigor - not layering an unvalidated ranking on a validated rule.



## Cross-system overlap (Spread Mid-Season Dog + Moneyline Unranked Favorite Dog) - Aug 2026

Tested whether games flagged by BOTH approved systems show stronger ML
ROI than the Moneyline system alone. Pooled overlap looked much
stronger (+18.0% vs +5.8%), but year-by-year reveals this is an
illusion: overlap sample is tiny per year (7-16 games), wildly
inconsistent (+0.6% to +52.0%), and NEGATIVE in 2025 (-17.8%, n=9) -
the one year that matters most. Non-overlap group, despite a lower
headline number, is actually more trustworthy: 5/5 years profitable in
a tight, believable range (+3.1% to +13.7%).

**Conclusion: cross-system overlap is NOT a validated confidence
signal** - the flashier pooled number is a small-sample illusion, not
real value-add. Unranked Favorite Dog should be used as its own,
standalone system - do not filter/prioritize by Spread agreement.