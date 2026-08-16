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