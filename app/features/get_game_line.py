"""
Line-source logic. Two distinct use cases with different needs:

1. HISTORICAL/TRAINING (get_best_line_for_game): a single canonical line
   per game is correct here - CFBD provider-priority (Bovada -> DraftKings
   -> other), unchanged from original design.

2. LIVE PREDICTION (get_live_book_lines / get_live_book_lines_batch):
   DraftKings and FanDuel can genuinely disagree enough to flip a bet
   decision (confirmed real, Aug 2026). The batch version exists because
   the per-game version cost 333ms/game in real testing - almost
   entirely database round-trip overhead - batching cuts a 51-game
   slate from ~17s down to one query.
"""
from collections import defaultdict
from app.models import CFBDBettingLine, OddsSnapshot

PROVIDER_PRIORITY = ["Bovada", "DraftKings", "ESPN Bet", "William Hill (New Jersey)", "consensus"]
LIVE_BOOK_PRIORITY = ["draftkings", "fanduel"]


class NormalizedLine:
    def __init__(self, spread, spread_open, over_under, over_under_open,
                 home_moneyline, away_moneyline, provider):
        self.spread = spread
        self.spread_open = spread_open
        self.over_under = over_under
        self.over_under_open = over_under_open
        self.home_moneyline = home_moneyline
        self.away_moneyline = away_moneyline
        self.provider = provider


def _get_line_from_odds_snapshots(game_id, db):
    for book in LIVE_BOOK_PRIORITY:
        snapshots = db.query(OddsSnapshot).filter(
            OddsSnapshot.game_id == game_id, OddsSnapshot.sportsbook == book,
        ).order_by(OddsSnapshot.pulled_at).all()
        if not snapshots:
            continue
        opening, current = snapshots[0], snapshots[-1]
        return NormalizedLine(
            spread=current.spread_home, spread_open=opening.spread_home,
            over_under=current.total, over_under_open=opening.total,
            home_moneyline=current.moneyline_home, away_moneyline=current.moneyline_away,
            provider=f"live_{book}",
        )
    return None


def get_best_line_for_game(game_id: int, db, cache=None):
    """Historical/training use - single canonical line, CFBD-first. Unchanged behavior."""
    if cache:
        lines = cache.lines_by_game.get(game_id, [])
    else:
        lines = db.query(CFBDBettingLine).filter(CFBDBettingLine.game_id == game_id).all()

    if lines:
        lines_by_provider = {line.provider: line for line in lines}
        for provider in PROVIDER_PRIORITY:
            if provider in lines_by_provider:
                return lines_by_provider[provider]
        return lines[0]

    if db is not None:
        return _get_line_from_odds_snapshots(game_id, db)
    return None


def get_live_book_lines(game_id: int, db):
    """
    Live prediction use, single game - returns {book_name: NormalizedLine}
    for EVERY book we have live-polled data for (draftkings, fanduel).
    Does NOT merge into one line - books can genuinely disagree.
    For multiple games, prefer get_live_book_lines_batch() instead -
    this per-game version costs ~333ms/game in real testing due to
    per-call database round-trips.
    """
    results = {}
    for book in LIVE_BOOK_PRIORITY:
        snapshots = db.query(OddsSnapshot).filter(
            OddsSnapshot.game_id == game_id, OddsSnapshot.sportsbook == book,
        ).order_by(OddsSnapshot.pulled_at).all()
        if not snapshots:
            continue
        opening, current = snapshots[0], snapshots[-1]
        results[book] = NormalizedLine(
            spread=current.spread_home, spread_open=opening.spread_home,
            over_under=current.total, over_under_open=opening.total,
            home_moneyline=current.moneyline_home, away_moneyline=current.moneyline_away,
            provider=f"live_{book}",
        )
    return results


def get_live_book_lines_batch(game_ids: list, db):
    """
    Batched version of get_live_book_lines() - one query for ALL games
    instead of one query per game. Confirmed via real timing (Aug 2026):
    the per-game version cost 333ms/game (17s for a 51-game slate),
    almost entirely database round-trip overhead, not real computation.
    Returns {game_id: {book: NormalizedLine}}.
    """
    all_snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id.in_(game_ids),
        OddsSnapshot.sportsbook.in_(LIVE_BOOK_PRIORITY),
    ).order_by(OddsSnapshot.pulled_at).all()

    by_game_book = defaultdict(list)
    for snap in all_snapshots:
        by_game_book[(snap.game_id, snap.sportsbook)].append(snap)

    results = defaultdict(dict)
    for game_id in game_ids:
        for book in LIVE_BOOK_PRIORITY:
            snapshots = by_game_book.get((game_id, book))
            if not snapshots:
                continue
            opening, current = snapshots[0], snapshots[-1]
            results[game_id][book] = NormalizedLine(
                spread=current.spread_home, spread_open=opening.spread_home,
                over_under=current.total, over_under_open=opening.total,
                home_moneyline=current.moneyline_home, away_moneyline=current.moneyline_away,
                provider=f"live_{book}",
            )

    return dict(results)