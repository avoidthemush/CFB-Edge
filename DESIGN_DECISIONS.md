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

## Player bio data completeness gap (Aug 2026)

~6% of players (3,935 of 65,753) came back from CFBD's roster endpoint with
no position, height, weight, or hometown - just a name and a class_year
value. Heavily concentrated in smaller/HBCU programs (some teams are 100%
sparse) - bio data traces back to recruiting-service profiles, which are
far less thoroughly documented outside major recruiting-industry coverage.
This is a genuine CFBD data limitation, not a bug in our sync.

149 of these were true duplicates of a complete record for the same
player (same name/team) - deleted. The remaining 3,786 are real players
with no other record - kept, flagged via players.has_complete_bio=False.
Any feature/analysis requiring position or physical data should filter or
account for this flag rather than assume full coverage.

## class_year format inconsistency (Aug 2026) - UNRESOLVED

class_year sometimes holds a small integer (0-6, apparent years-of-
eligibility) and sometimes a calendar year (2021-2025) - inconsistent
even among players WITH complete bio data, so it's not explained by the
sparse-record issue above. Root cause not yet diagnosed - possibly CFBD's
roster payload format differs across the seasons we backfilled. Do not
use class_year as a model feature until this is investigated further.
Revisit during feature engineering, not blocking current work.


## Defensive returning production - null percentages (Aug 2026)

70 of 1,393 team-year rows in defensive_returning_production have
percent_havoc_returning = None. Confirmed via check_null_havoc.py: these
are all small/D2 programs where CFBD's player_season_stats coverage is
thin (1-5 players with any stat row at all for that team-year), and by
chance none of those few players recorded a TFL, pass defended, or
fumble recovery. total_havoc_prior_year = 0 in every case, making the
percentage mathematically undefined (0/0) - left as NULL rather than
forced to a misleading 0% or 100%. Not a bug; same underlying data
sparsity pattern already documented for players.has_complete_bio.

## Defensive returning production - 2026 roster fallback (Aug 2026)

2026 has no player_season_stats data yet (season not played). For any
year with zero stats rows anywhere, calc_defensive_returning_production.py
falls back to players.team_id (current roster) instead of stats-based
team membership to determine who's "returning." This is intentionally
scoped to only apply when a year has NO stats data at all, so it never
overrides real historical calculations for a past season. Note: roster-
fallback years measure returning slightly differently than stats-based
years (roster presence vs. "recorded a stat"), which tends to produce
somewhat higher returning percentages - worth keeping in mind if 2026
rows are ever compared directly against historical rows during modeling.



## JSON-safe serialization for raw_json columns (Aug 2026)

Transfer portal sync failed on first run: CFBD's client returns some
fields as Python Enum objects (e.g. eligibility) rather than plain
strings, and to_dict() doesn't fully flatten these or nested datetimes.
Postgres JSON columns can't serialize either directly.

Fix: app/pipeline/sync_transfer_portal.py has a _json_safe() recursive
helper (datetimes -> ISO strings, enums -> .value) applied before writing
to any raw_json column. Worth reusing this pattern in any future sync
script whose source model might return enums - copy the helper rather
than re-discovering this bug.



## Silent duplicate table from incomplete rename (Aug 2026)

rename_returning_production_table.py was run once, appeared successful,
but the rename never actually took effect on the database (root cause
unclear - possibly run in a session where the commit didn't apply).
Every table query since then silently pointed at a brand-new EMPTY table
init_db.py created under the new name (create_all() only creates tables
that don't exist - it had no way to know the "real" table was sitting
under the old name). Result: offensive_returning_production appeared to
work (no errors, valid queries) but was 100% null/missing for every row,
while the real 792 rows of verified data sat orphaned under the old
returning_production name, completely invisible.

This was only caught via the cross-table integration check
(check_integration.py) - none of the individual per-table QC checks
would have caught it, since querying the (correct, but wrong) empty
table returns valid "no results" rather than an error. Lesson: a rename
or schema-restructure script should always be followed by a direct
row-count verification against the database (see
check_table_rename.py pattern) before assuming success, not just trusted
because it printed a success message.