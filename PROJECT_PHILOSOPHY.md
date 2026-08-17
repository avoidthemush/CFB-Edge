# Core Project Philosophy — CFB Edge

## The central rule (established Aug 2026, after 6 failed and 1
successful Total approach proved this empirically, not just theoretically)

**We are not fortune tellers. We are not trying to out-predict a
sportsbook's own analysts, data, and resources — we cannot, and
shouldn't try to.** A real sportsbook has play-by-play data, injury
reports, betting-percentage feeds, and human analyst teams we will
never fully replicate. Competing with them on "who predicts the final
score better" is a losing game by design.

**What we CAN do: find moments where the market's own line-setting
process has a structural crack.** Books must post a number for every
game, every week, at scale - that process is imperfect, and those
imperfections are genuinely findable without needing to out-analyze the
game itself.

## Two distinct kinds of "market-relative" edge - both legitimate,
proven to behave differently

**Type A — Prediction vs. Market:** Build our own independent prediction
of the outcome (using team strength, matchups, etc.), then bet only when
our prediction disagrees enough with the market's posted number. This is
what Spread's two approved systems (General Model, Mid-Season Dog) do.
Real, proven, works for Spread.

**Type B — Market Self-Consistency / Anomaly Detection:** Skip
prediction entirely. Check whether the market's OWN number looks
inconsistent with how it typically prices similar situations (e.g. "is
this total unusually low/high for games with this combined pace level,
based on recent history"). This is what Total's approved "Market
Deviation" system does. No Type A approach worked for Total across 6
different attempts; the one Type B approach we tried worked immediately
and cleared all 4 test years, including the 2 years that broke every
Type A attempt.

## Standing instruction for all future model work (Spread, Total,
Moneyline, and anything after)

1. **Try Type B (market anomaly detection) explicitly, every time** -
   don't only reach for Type A (build-a-better-prediction) by default,
   even though it's the more intuitive starting point.
2. **When Type A struggles repeatedly (as it did for Total), that's a
   signal to pivot to Type B, not to keep refining Type A features.**
3. **Spread has NOT yet been tested with a Type B approach** - both
   approved Spread systems are Type A. This is real, queued, unexplored
   work - not something to assume is already covered.
4. **Moneyline should be approached with both types in mind from the
   start**, not built as a copy of the Spread process by default.

This is a standing rule for the project, not a one-time insight -
revisit this document before starting any new model or any new search
within an existing model.