"""
Implements the Bovada -> DraftKings -> other provider-priority fallback
decided in DESIGN_DECISIONS.md. Returns the single best available line
for a game from cfbd_betting_lines (historical training data source -
NOT live odds, which is DK/FanDuel-only via a separate pipeline).
"""
from app.models import CFBDBettingLine

PROVIDER_PRIORITY = ["Bovada", "DraftKings", "ESPN Bet", "William Hill (New Jersey)", "consensus"]


def get_best_line_for_game(game_id: int, db):
    lines = db.query(CFBDBettingLine).filter(CFBDBettingLine.game_id == game_id).all()
    if not lines:
        return None

    lines_by_provider = {line.provider: line for line in lines}

    for provider in PROVIDER_PRIORITY:
        if provider in lines_by_provider:
            return lines_by_provider[provider]

    return lines[0]