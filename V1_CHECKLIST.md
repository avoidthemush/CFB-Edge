# Path to CFB Edge v1 — Data Readiness Checklist

Goal: everything on the data side genuinely ready before starting the
modeling phase. Organized by priority, not by when it was built.

## A. Must fix before v1 (real gaps, no workaround)

- [ ] **Bring annual_maintenance.py current.** It only runs venues/teams/
      games/odds-crosswalk right now. Missing: ratings, advanced stats,
      team ATS, team talent, recruiting, offensive returning production,
      defensive returning production calc, players, player_season_stats,
      poll rankings, transfer portal, coaches. Until this is fixed, there
      is no single trustworthy "refresh everything" command - a real gap
      given the whole point of building it.
- [ ] **Update MAINTENANCE.md to match** once annual_maintenance.py is
      current - the doc and the code have to stay in sync or the doc
      becomes actively misleading.
- [ ] **Run one full annual_maintenance.py pass end-to-end** after the
      fix, on both machines, confirming a clean audit with no errors.
- [ ] **Cross-table integration check.** Every table has been validated
      in isolation; none have been validated together. Pick several real
      games (a mix of years, a mix of "big program" and "smaller
      program") and confirm ALL related data resolves correctly when
      joined: game -> teams -> venue -> odds (CFBD lines) -> ratings ->
      advanced stats -> offensive/defensive returning production. This
      is the test that actually proves the data is usable for modeling,
      not just individually correct.
- [ ] **Resolve player_season_stats.usage_overall.** Column exists,
      never populated (0% - decided against defensive use, never
      circled back for offense). Either sync it for offensive positions
      via get_player_usage, or drop the column and note why in
      DESIGN_DECISIONS.md. Leaving a silently-empty column is a trap for
      future-us during feature engineering.

## B. Should validate before v1 (untested code paths)

- [ ] **Run sync_live_odds() for real at least once**, even against
      sparse preseason markets, to confirm the DK/FanDuel filtering,
      team-name resolution via the crosswalk, and game-matching logic
      all work against real API responses - not just reviewed code.
      Currently zero rows in odds_snapshots.
- [ ] **Run mark_closing_lines() for real at least once**, once any
      live-odds data exists and at least one tracked game has kicked
      off. Can't fully validate until there's a real "before vs. after
      kickoff" case to check against.
- [ ] **Confirm class_year is safe to ignore for now.** Documented as
      unresolved (mixed integer/calendar-year values). Not blocking data
      readiness, but should be explicitly excluded from any early
      feature list rather than accidentally used.

## C. Explicitly deferred (documented, acceptable to leave for now)

- [ ] **Weather (historical + live).** Blocked on OpenWeather One Call
      3.0/4.0 subscription setup on your end. Both sync scripts need to
      be built once that's in place.
- [ ] **Betting line provider-priority fallback logic** (Bovada ->
      DraftKings -> other). Decision is documented in
      DESIGN_DECISIONS.md; implementation is feature-engineering work,
      not data-gathering work - correctly belongs in the modeling phase,
      not this checklist's blocking items.
- [ ] **Game-level player stats** (player_id + game_id granularity).
      Deliberately scoped out earlier - season-level was sufficient for
      defensive returning production. Revisit only if modeling reveals a
      real need for game-level detail.

## D. Operational readiness (post-v1, not blocking data completeness)

- [ ] **Railway scheduler** for recurring jobs (odds polling ramping up
      toward kickoff, weather pulls, score updates). Currently zero
      automation - everything's been run manually tonight. Needed before
      the system can run unattended during the season, but the model can
      be built and validated against historical data without it.
- [ ] **Odds polling cadence** actually implemented per the "multiple
      times a day as kickoff approaches" plan discussed earlier -
      currently just a plan, not code.

## E. Nice-to-have (would help, not required)

- [ ] **Data dictionary** - a single reference doc listing every table,
      every column, and a one-line meaning for each. Given how much
      custom logic is baked into this build (havoc-rate defensive
      metric, JSONB raw fields, the CFBD-vs-Odds-API-vs-our-own-naming
      distinctions), this would meaningfully speed up feature engineering
      versus re-deriving "what does this column mean" from
      DESIGN_DECISIONS.md each time.
- [ ] **Final row-count snapshot** across all 21 tables, saved somewhere
      (even just appended to BUILD_CHECKLIST.md), as a known-good
      baseline to compare against if something looks off later.

## Definition of done for v1

All of Section A checked, all of Section B checked or consciously
accepted as a known gap, Section C explicitly acknowledged as deferred
(not forgotten), and Section D/E logged as intentional post-v1 work -
not silently skipped.