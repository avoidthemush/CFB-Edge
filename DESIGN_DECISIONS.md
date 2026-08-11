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