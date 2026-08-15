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

## Live odds decimal vs. American format bug (Aug 2026)

First real run of sync_live_odds() produced garbage price values (spread
prices like "2", moneylines like "1"/"4"). Root cause: The Odds API
defaults to decimal odds format unless oddsFormat=american is explicitly
requested. Our sync never specified it, got decimal values (1.91, 3.6,
etc.), and those got silently truncated by the Integer column type
(1.91 -> 2, 3.6 -> 4) rather than erroring - meaning the corruption was
completely silent until we manually inspected a sample row.

Fixed by adding oddsFormat=american to the request params. 185 corrupted
rows were deleted and re-pulled rather than converted in place.

Lesson: when a third-party API supports multiple representations of the
same underlying value (formats, units, scales), always explicitly specify
the format wanted rather than relying on a default - defaults can differ
from what a naive read of the field name suggests, and a format mismatch
can silently produce plausible-looking-but-wrong numbers rather than an
obvious error.

## 2021 weather coverage gap (Aug 2026)

2021 has only 853/2,454 games (35%) with weather data, versus ~99%+
coverage in 2022-2025. Checked via check_2021_weather_gap.py: the gap is
spread evenly across every week of the season (25-35% coverage
throughout, no week fully missing) rather than concentrated in one
stretch - this rules out a sync bug (which would likely show a dead
zone) and points to CFBD simply having less complete weather source data
for their oldest tracked season. Not something we can fix on our end;
noted as a known historical data limitation, consistent with similar
patterns seen in team_talent and player bio completeness for older/
smaller-coverage data.


## CoachSeason can have multiple rows per team-year (Aug 2026)

Discovered while building point-in-time features: coach_seasons can
legitimately contain more than one row for the same (team_id, year) -
e.g. South Florida 2025 has both Alex Golesh (9-3, the actual season-long
HC) and Kevin Patrick (0-1, an interim/one-game coach). This reflects
real mid-season coaching changes and is correct, not a sync bug -
sync_coaches.py is capturing exactly what CFBD provides.

Any code querying "who is the coach of team X in year Y" needs an
explicit tie-break rule rather than .first()/arbitrary selection - the
convention established in app/features/build_team_features.py and
feature_cache.py is: the row with the most games coached (wins+losses)
is treated as the primary coach for that season. Apply this same rule
in any future code that looks up a team's coach for a given year.

## Historical range extended to 2015 (Aug 13, 2026)

Original project scope was 2021-2026 (transfer-portal era). During
Spread model ATS backtesting, sample size (~800-2,300 FBS games per
test) was too small to distinguish real edge from noise - a promising-
looking pattern in the 2025 holdout failed to replicate against 2024,
confirming it was likely noise, not a real discovery.

Rather than assume a historical cutoff, verified CFBD's actual data
availability per-source (check_full_historical_scope.py,
check_player_data_historical.py). Found the transfer-portal-2021
boundary had been incorrectly over-applied to player-level data
generally - roster, player season stats, player usage, and offensive
returning production are all genuinely available from 2015, three years
further back than originally assumed. Only transfer_portal_entries
itself is truly 2021-bound. Team ATS is bound to 2019 (a separate, real
CFBD limitation, unrelated to the transfer portal).

Full historical backfill (2015-2020) executed via backfill_to_2015.py
in 6 staged steps, ~4,500+ API calls total (dominated by the roster
per-team loop), all verified clean (near-zero skip/failure rates
throughout, consistent with the original 2021-2026 build's data
quality). One process gap caught and fixed: sync_coaches() was
initially omitted from the backfill stages entirely.

## teams.division staleness from historical backfill order (Aug 2026)

backfill_to_2015.py's Stage 1 synced teams for 2015-2020 in ascending
order, with 2020 processed last. Since teams.division/conference are
NOT year-scoped (one row per team, reflecting whatever the most recent
sync_teams() call set), this silently overwrote every team's
classification back to their 2020 status - misclassifying every team
that transitioned into FBS since 2021 (Jacksonville State, Sam Houston,
Sacramento State, North Dakota State, etc.) as non-FBS.

Caught via a suspicious FBS-filter row-count drop when regenerating
training data (809 -> 739 games for the same 2025 season, which should
be impossible). Fixed by re-running sync_teams(year=CURRENT_SEASON) and
regenerating the affected filtered CSVs. backfill_to_2015.py updated so
CURRENT_SEASON is always synced last in any future historical backfill,
ensuring teams.division always reflects the present, not a leftover
historical loop year.

## Standing workflow rule (Aug 2026)

Before any git push, do a root-folder cleanup pass first - move
one-off/investigation scripts to the appropriate archive subfolder
before committing, not after. Keeps the repo history clean rather than
needing later cleanup commits.

## Odds API: collect all books, restrict usage to DK/FanDuel (Aug 2026)

Confirmed via The Odds API docs: request cost is per market x region,
NOT per bookmaker returned within that region. Pulling all ~40 available
US-region books costs the exact same 1 credit per market as pulling just
DraftKings/FanDuel. Given this, sync_live_odds() no longer filters by
bookmaker at collection time - the full backend archive stores every
available book for completeness (same "better to have it and not need
it" principle applied throughout this project).

The DraftKings/FanDuel-only restriction for the dashboard/model/betting
decisions is enforced at the USAGE layer instead - see
LIVE_BOOK_PRIORITY in app/features/get_game_line.py, which only looks
for DK/FanDuel snapshots when building a prediction, regardless of how
many other books exist in odds_snapshots. This means we could expand
which books the dashboard trusts later (e.g. adding a third book) without
needing to re-poll or backfill anything - the data's already there.