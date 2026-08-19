# Final Rollout Checklist

Cross-phase collection point for items deliberately deferred during V1
(data), V2 (models), or V3 (dashboard/automation) - things that are
real, necessary, but don't block progress within their own phase.
Nothing gets forgotten; everything gets done before actual go-live.

## From V1 (data)
- [ ] Run one full `annual_maintenance.py` pass end-to-end, both
      machines. Deliberately deferred throughout V1 and V2 - nothing to
      gain from running it early vs. as a final pre-launch validation
      step, since it's meant to simulate exactly what the V3 scheduler
      will do on a recurring basis. Best run once V3's scheduler design
      is finalized, so any needed fixes get made once, not twice.

## From V2 (models)
- [ ] Final V2 summary doc: consolidated overview of all three models
      (Spread: General Model + Mid-Season Dog; Total: Pace/Field
      Position/Travel/Wind Deviation + Home Favorite tag; Moneyline:
      Unranked Favorite Dog) - performance stats, known limitations,
      links to each full feature log. (Moved here from
      V3_DASHBOARD_PLAN.md for consolidation - see note there.)

## From V3 (to be added as V3 work proceeds)
- (nothing yet - will populate as V3 checklist items get deliberately
  deferred rather than done in-line)