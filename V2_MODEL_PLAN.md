# V2 — Model Build Plan

Companion to V1_CHECKLIST.md. V1 was data-gathering; this is turning that
data into working Spread/Total/Moneyline predictions.

## Naming convention (applies to all three targets)

Every prediction target (Spread, Total, Moneyline) gets built in two
phases, producing two distinct model artifacts. Never conflate these or
deploy the wrong one:

- **Validation model** — trained on 2021-2024 only, tested against 2025
  as a true holdout. Exists purely to prove the methodology/features
  work before committing further. Never used for real predictions.
- **Production model** — trained on 2021-2025 (once validation model
  passes). This is the model that actually generates 2026 predictions.
  2026 is never used in training - it's the true live test as the season
  unfolds.

Phase order per target: build validation model -> evaluate against 2025
-> only if it meets a bar we're satisfied with, retrain as production
model on 2021-2025 -> that's what goes live.

## 1. Prediction targets

- **Spread** — predict point differential (home_score - away_score)
- **Total** — predict combined points (home_score + away_score)
- **Moneyline** — predict win probability (classification), not just
  binary win/loss

Open question: three fully separate models, or one shared feature/
embedding base with three output heads? Default to three separate
models initially (simpler, easier to debug independently) - can revisit
a shared architecture later if there's a clear reason to.

## 2. Train/test split (temporal, not random)

- Validation: train 2021-2024, test 2025
- Production: retrain 2021-2025, live-test 2026 (never trained on)
- No random shuffling across years - sports data is time-ordered;
  a random split would leak future information into training and
  produce falsely optimistic results

## 3. Feature engineering layer

Raw tables are entity-level (a team's SP+ for a year, a team's returning
production for a year). The model needs game-level, matchup-relative
features. Key design question to resolve before building: differentials
(home_value - away_value) vs. raw paired values (home_value AND
away_value as separate columns) vs. both. Differentials are usually more
directly predictive and reduce dimensionality, but raw values preserve
information a differential can hide (e.g. two elite teams both near 100
looks the same differential-wise as two mediocre teams both near 50).
Likely need both in practice.

Feature sources already available from V1:
- Ratings differential (SP+, SRS, Elo, FPI - home vs away)
- Advanced/adjusted stats differential (success rate, PPA, havoc, etc.)
- Offensive + defensive returning production differential
- Team talent / recruiting differential
- Team ATS history
- Weather (temp, wind, precip - primarily a Total feature, outdoor games only)
- Betting line itself as a feature/baseline (see Evaluation, below)
- Venue/travel context (home/away, neutral site, distance - not yet
  built as a feature, may need a simple travel-distance calc)
- Coaching context (tenure, historical record) - available, not yet
  used

## 4. Data leakage risk - RESOLVED APPROACH

Point-in-time capability varies by source, verified against the actual
CFBD client (not assumed):

**True point-in-time available (pulled per-week via API):**
- team_stats (raw box score) - API supports end_week
- team_advanced_stats (efficiency/PPA/havoc) - API supports end_week
- Elo rating - API supports week directly (rating_snapshots.week column
  already exists in schema, just never populated until now)

**NOT point-in-time capable via API (season-final only, no week param):**
- SP+, SRS, FPI ratings - locked to prior-completed-season value only
- Team ATS record - locked to prior-completed-season value only (or
  self-computed cumulative from cfbd_betting_lines + games if ever
  worth the extra build)

**Already correctly prior-season-baseline by design, no change:**
- offensive_returning_production, defensive_returning_production,
  team_talent, recruiting_classes

### The blending approach (this is the actual model-accuracy decision)

Raw weekly point-in-time stats are noisy early in a season (2-3 games is
a small sample for success rate/PPA). Rather than treat "prior-season
baseline" and "in-season point-in-time" as alternatives, BOTH are used
together via blending:

- Early season (small in-season sample) -> weight prior-season final
  stats heavily, in-season stats lightly
- Later season (larger in-season sample) -> weight flips toward the
  current season's actual performance
- Exact blending curve/cutoffs to be defined during feature-engineering
  build, informed by games-played-so-far as the sample-size proxy

CRITICAL: the blending function must be ONE SHARED function, used
identically by both the training-feature builder and the live-prediction
feature builder. Two separate implementations that could drift apart
would silently reintroduce train-serving skew. This is core shared
infrastructure, not a training-only script.

### 2026 applicability

This entire approach is designed to work identically for live 2026
predictions, not just historical backtesting - the same blend of
"2025 final" + "2026 so-far" applies to a live Week 5 2026 prediction
the same way "2023 final" + "2024 so-far" applies to a historical Week 5
2024 backtest game. This creates a real dependency: the weekly stats/
advanced-stats/Elo sync must actually RUN during the live season for
this to work - ties directly to the Railway scheduler item in
V1_CHECKLIST.md Section D, which moves from "nice to have" to "required
before going live" as a result of this decision.

## 5. Model type

Gradient-boosted trees (XGBoost or LightGBM) as the starting point -
standard, strong baseline for tabular sports data, more interpretable
than deep learning, appropriate for this data size. Revisit only if
there's a clear reason to (e.g. a specific pattern trees can't capture).

## 6. Evaluation approach

Compare model predictions against actual closing lines (from
cfbd_betting_lines and, once enough live data exists, odds_snapshots
with is_closing_line=True). The real question isn't "is the model
accurate in isolation" but "does the model beat or match the market" -
a model that just re-derives the closing line isn't providing an edge,
even if its raw accuracy looks good. Need a defined success metric
before evaluating (e.g. ATS win rate against closing spread, total
prediction error vs. closing total, moneyline calibration vs. implied
probability).

## Deferred to live-environment checklist (not V2 build scope)

- Tracking production model performance/accuracy as the actual 2026
  season unfolds (rolling ATS record, calibration drift, etc.) - real
  requirement, belongs with the live scheduler/operational work
  (V1_CHECKLIST.md Section D), not the initial model build.

## Build order (proposed)

1. Resolve data leakage rules (Section 4) - DONE
2. Build the weekly point-in-time sync layer (team stats, advanced
   stats, Elo) - IN PROGRESS (sync_weekly_stats.py written, single-year
   test pending)
3. Build the feature engineering layer (Section 3) for one target first
   (suggest Spread - most data available, most standard starting point)
4. Build + evaluate Spread validation model
5. If it clears the bar, retrain as Spread production model
6. Repeat for Total, then Moneyline
7. Only then: live tracking / operational work