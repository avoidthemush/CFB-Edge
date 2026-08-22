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
- [ ] Add a `/games/week/{week}` endpoint returning the FULL schedule
      (every FBS-vs-FBS game), not just games with a qualifying pick.
      Needed so the game-card grid can show the complete week with
      qualifying games subtly highlighted, rather than only ever
      displaying games that already qualify.
- [ ] Expose venue (name, city/state) per game - data exists in `venues`
      table, not yet joined into any API response.
- [ ] Expose weather (temp, wind, condition) per game - data exists in
      `weather_snapshots`, not yet exposed via API.
- [ ] Expose each team's rolling last-10 (ATS/O-U/SU) record per game -
      data exists in `team_recent_form` (built during V3 automation),
      not yet exposed via API.
- [ ] Compute and expose each team's current SEASON record (W-L) -
      doesn't exist anywhere yet, would need a new query/endpoint.
- [ ] Weather icon mapping is BUILT and ready in the frontend
      (WeatherIcon component maps condition strings to Rain/Sun/Snow/
      Wind/Cloud icons) - just needs the API to actually expose a real
      `weather_condition` string per game (data exists in
      weather_snapshots, not yet surfaced via API).