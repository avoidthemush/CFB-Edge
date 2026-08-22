# Frontend-Driven Backend TODO

Real backend gaps discovered WHILE building the frontend, deliberately
NOT fixed immediately - logged here and addressed together in a
dedicated pass when the user says it's time, so frontend momentum
isn't interrupted by context-switching to backend work mid-build.

## Open items
- [ ] Add a real `pooled_roi` field to betting_systems (currently only
      pooled_win_rate exists) - needed so the dashboard can show
      Moneyline's actual ROI instead of a misleading raw win rate.
- [ ] market_spread_current / market_spread_open are overloaded fields
      - mean "spread" for Spread/Moneyline rows but "total" for Total
      rows. Consider renaming to something bet-type-agnostic
      (market_line_current / market_line_open) or adding a clearer
      field, since the current naming requires the frontend to "know"
      the true meaning based on bet_type.