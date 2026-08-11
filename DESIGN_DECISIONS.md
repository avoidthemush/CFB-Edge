# Design Decisions

Running log of non-obvious choices made during CFB Edge development, so the
reasoning doesn't get lost in chat history.

## Betting line provider priority (Aug 2026)

CFBD's historical lines come from 10 different providers with wildly
different completeness (see audit_provider_completeness.py). Bovada is the
most complete (100% spread/total, both open+close, ~88% moneyline).
DraftKings is second best but weaker on over_under_open specifically (30%).
Most other providers (William Hill, consensus, Caesars, numberfire,
teamrankings) only carry closing spread/total - 0% on opens and moneylines.

Decision: when building model features, use a priority fallback per game -
prefer Bovada, then DraftKings, then whatever's available - rather than
averaging across providers or picking arbitrarily. Implement this in the
feature-engineering step, not the sync layer (sync_betting_lines.py stores
all providers as-is; selection happens downstream).

Live 2026+ odds are separately and intentionally scoped to DraftKings and
FanDuel only, via The Odds API (see BOOKMAKERS constant in
sync_betting_lines.py) - this provider-priority decision is specifically
about the CFBD historical backfill, which doesn't carry FanDuel at all.

## CFBD internal naming inconsistencies (Aug 2026)

Discovered while building recruiting sync: CFBD's own endpoints don't
always agree on team name spelling. The canonical Teams endpoint uses one
spelling; other endpoints (confirmed so far: Recruiting) sometimes use a
different one for the same school (e.g. "Southeastern Louisiana" vs
"SE Louisiana", "Albany" vs "UAlbany"). This is separate from the Odds API
crosswalk problem (external provider, different naming conventions
entirely) - this is CFBD disagreeing with itself across its own endpoints.

Fix: app/pipeline/team_resolver.py - a shared CFBD_NAME_ALIASES dict and
resolve_team_id() helper, used by every sync script instead of a raw
dict lookup. New sync scripts should use this from the start. When a sync
script reports "no team match," check team_resolver.py's alias list first
before assuming it's a genuinely different/untracked school.

## Returning production - full field capture + defense gap (Aug 2026)

Decision: expand returning_production table to capture ALL fields CFBD
provides (not just the 3-column overall/offense/defense simplification
originally designed) - philosophy is to capture available data now even
if we don't yet know which fields become model features, rather than
under-capture and have to backfill later. Applies as a general principle
going forward for any endpoint with rich data, not just this one.

Full field list from CFBD (offense-only): percentPPA, percentPassingPPA,
percentReceivingPPA, percentRushingPPA, usage, passingUsage,
receivingUsage, rushingUsage, plus raw total (non-percent) PPA versions
of each. Needs a schema migration on returning_production to add real
columns for these instead of cramming into overall_pct/offense_pct.

Defense gap: CFBD has NO defensive returning-production metric - PPA is
an offense-centric concept (points added per play), doesn't have a clean
defensive equivalent in their data model. Plan: build our own proxy
metric from pieces we already have/can get - roster year-over-year
comparison, player usage stats filtered to defensive positions, draft
picks lost (NFL early departures), transfer portal outflow. This is a
custom build, not a pull-from-endpoint task - tackle as its own focused
work item, not bolted onto the returning_production sync.