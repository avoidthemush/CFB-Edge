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

## 4. Data leakage risk - explicit rules needed

Several tables could leak the answer if pulled naively:
- A team's SEASON-END SP+/ratings technically include the outcome of
  the very game being predicted, if not handled carefully. Need either
  point-in-time (as-of-that-week) ratings, or explicit lag (use prior
  week's/prior season's rating only).
- Same risk applies to team_season_stats, team_advanced_stats,
  team_ats - all are season aggregates that could implicitly contain
  the target game's result.
- Betting lines themselves are fine to use as a FEATURE (the market's
  own prediction) but the actual game outcome obviously can never be a
  feature.

This needs a concrete resolution (likely: build features from data
available strictly BEFORE each game's kickoff, using prior-week or
prior-season snapshots only) before any model training starts - not an
afterthought.

## 5. Model type

Gradient-boosted trees (XGBoost or LightGBM) as the starting point -
standard, strong baseline for tabular sports data, more interpretable
than deep learning, appropriate for this data size. Revisit only if
there's a clear reason to (e.g. a specific pattern trees can't capture).

## 6. Evaluation approach

Compare model predictions against actual closing lines (from
cfbd_betting_lines and, once enough live data exists,