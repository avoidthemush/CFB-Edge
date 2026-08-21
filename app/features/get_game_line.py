"""
Line-source logic. Two distinct use cases with different needs:

1. HISTORICAL/TRAINING (get_best_line_for_game): a single canonical line
   per game is correct here - CFBD provider-priority (Bovada -> DraftKings
   -> other), unchanged from original design.

2. LIVE PREDICTION (get_live_book_lines / get_live_book_lines_batch):
   DraftKings and FanDuel can genuinely disagree, so each book's lines
   are returned separately. Now KICKOFF-AWARE (Aug 2026): only
   snapshots recorded BEFORE the game's start_date are considered for
   "current"/qualification purposes - a post-kickoff snapshot is
   meaningless for a betting decision and would corrupt the definition
   of "closing line" (the last snapshot before kickoff, not just the
   last snapshot we happen to have polled).
"""
from collections import defaultdict
from app.models import CFBDBettingLine, OddsSnapshot

PROVIDER_PRIORITY = ["Bovada", "DraftKings", "ESPN Bet", "William Hill (New Jersey)", "consensus"]
LIVE_BOOK_PRIORITY = ["draftkings", "fanduel"]


class NormalizedLine:
    def __init__(self, spread, spread_open, over_under, over_under_open,
                 home_moneyline, away_moneyline, provider, is_closing=False):
        self.spread = spread
        self.spread_open = spread_open
        self.over_under = over_under
        self.over_under_open = over_under_open
        self.home_moneyline = home_moneyline
        self.away_moneyline = away_moneyline
        self.provider = provider
        self.is_closing = is_closing  # True once kickoff has passed - this is now the permanent "close"


def _build_normalized_line(snapshots, kickoff_time):
    """
    snapshots: all snapshots for one game+book, sorted oldest-first.
    kickoff_time: the game's start_date (may be None for games missing it).
    """
    if not snapshots:
        return None

    pre_kickoff = snapshots
    if kickoff_time is not None:
        pre_kickoff = [s for s in snapshots if s.pulled_at < kickoff_time]

    if not pre_kickoff:
        # No pre-kickoff snapshot exists at all (e.g. we only started
        # polling after the game already began) - nothing usable.
        return None

    opening = pre_kickoff[0]
    latest_pre_kickoff = pre_kickoff[-1]
    has_post_kickoff_data = kickoff_time is not None and len(pre_kickoff) < len(snapshots)

    return NormalizedLine(
        spread=latest_pre_kickoff.spread_home, spread_open=opening.spread_home,
        over_under=latest_pre_kickoff.total, over_under_open=opening.total,
        home_moneyline=latest_pre_kickoff.moneyline_home, away_moneyline=latest_pre_kickoff.moneyline_away,
        provider="live",
        is_closing=has_post_kickoff_data,  # kickoff has passed - this snapshot is now the permanent close
    )


def _get_line_from_odds_snapshots(game_id, db, kickoff_time=None):
    for book in LIVE_BOOK_PRIORITY:
        snapshots = db.query(OddsSnapshot).filter(
            OddsSnapshot.game_id == game_id, OddsSnapshot.sportsbook == book,
        ).order_by(OddsSnapshot.pulled_at).all()
        line = _build_normalized_line(snapshots, kickoff_time)
        if line is not None:
            line.provider = f"live_{book}"
            return line
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


def get_live_book_lines(game_id: int, db, kickoff_time=None):
    """
    Live prediction use, single game - returns {book_name: NormalizedLine}
    for EVERY book we have USABLE (pre-kickoff) live-polled data for.
    kickoff_time should be the game's start_date - if provided, any
    snapshot recorded after kickoff is excluded from "current" and the
    line is flagged is_closing=True once kickoff has passed.
    """
    results = {}
    for book in LIVE_BOOK_PRIORITY:
        snapshots = db.query(OddsSnapshot).filter(
            OddsSnapshot.game_id == game_id, OddsSnapshot.sportsbook == book,
        ).order_by(OddsSnapshot.pulled_at).all()
        line = _build_normalized_line(snapshots, kickoff_time)
        if line is not None:
            line.provider = book
            results[book] = line
    return results


def get_live_book_lines_batch(game_ids: list, db, kickoff_times: dict = None):
    """
    Batched version - one query for ALL games instead of one per game.
    kickoff_times: optional {game_id: start_date} dict. If not provided,
    kickoff-awareness is skipped (backward-compatible - callers that
    don't pass this behave exactly as before). Returns
    {game_id: {book: NormalizedLine}}.
    """
    kickoff_times = kickoff_times or {}

    all_snapshots = db.query(OddsSnapshot).filter(
        OddsSnapshot.game_id.in_(game_ids),
        OddsSnapshot.sportsbook.in_(LIVE_BOOK_PRIORITY),
    ).order_by(OddsSnapshot.pulled_at).all()

    by_game_book = defaultdict(list)
    for snap in all_snapshots:
        by_game_book[(snap.game_id, snap.sportsbook)].append(snap)

    results = defaultdict(dict)
    for game_id in game_ids:
        kickoff_time = kickoff_times.get(game_id)
        for book in LIVE_BOOK_PRIORITY:
            snapshots = by_game_book.get((game_id, book))
            if not snapshots:
                continue
            line = _build_normalized_line(snapshots, kickoff_time)
            if line is not None:
                line.provider = book
                results[game_id][book] = line

    return dict(results)