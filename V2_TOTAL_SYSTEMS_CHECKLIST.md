# Total Market-Deviation Candidates — Systematic Checklist

From the 9,968-combination massive search, ranked by recurrence in the
top 40. Each gets the SAME rigor: independent-split recheck ->
independence check (not just a proxy for team quality/pace) -> full
4-fold walk-forward + bootstrap. Not stopping at the first success -
working through all real candidates before calling this phase done.

## Recurrence tally (from top 40)
| Dimension | Recurrence | Status |
|---|---|---|
| field_position | 12 | ✅ TESTED - APPROVED (Field Position Deviation) |
| pace | 8 | ✅ TESTED - APPROVED (Pace Deviation, found earlier) |
| travel | 5 | ⬜ NOT YET TESTED |
| wind | 5 | ⬜ NOT YET TESTED |
| def_ppa | 5 | ⬜ NOT YET TESTED |
| def_success_allowed | 3 | ⬜ NOT YET TESTED |
| temp | 3 | ⬜ NOT YET TESTED |
| third_down | 2 | ⬜ NOT YET TESTED |
| off_points_per_opp | 2 | ⬜ NOT YET TESTED |
| turnover_gap | 2 | ⬜ NOT YET TESTED |
| off_efficiency | 1 | ⬜ NOT YET TESTED (low priority, single occurrence) |

## Filter recurrence tally (from top 40)
| Filter | Recurrence | Status |
|---|---|---|
| early_season | 7 | Flagged as possibly fragile (small early-season samples, per Spread lesson) |
| favorite_home | 7 | ⬜ NOT YET TESTED as standalone angle |
| low_wind | 6 | Partially covered (appeared in field_position recheck) |
| high_total_open | 5 | ⬜ NOT YET TESTED |
| conference_games | 3 | ⬜ NOT YET TESTED |

## Process going forward
Test dimensions in recurrence order. For each: independent-split
recheck -> independence check -> full walk-forward + bootstrap if it
passes both. Log EVERY result (pass or fail) in TOTAL_FEATURE_LOG.md,
not just successes. Only move to "done with this phase" once all
dimensions with recurrence >=3 have been checked.