"""
Converts American odds to implied probability, then removes the
sportsbook's built-in vig (house edge) so we get a FAIR probability to
compare against - without this, we'd be comparing our number against
an inflated one and every "edge" we find would be partly fake.

Uses the standard proportional devigging method: convert both sides to
raw implied probability, then scale both down so they sum to exactly 1.0.
"""


def american_odds_to_implied_prob(odds):
    if odds is None:
        return None
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)


def devig_two_way(home_odds, away_odds):
    """
    Returns (fair_home_prob, fair_away_prob), summing to exactly 1.0.
    Proportional method: scale each side's raw implied probability down
    by the same factor so the overpround (vig) is removed evenly.
    """
    home_raw = american_odds_to_implied_prob(home_odds)
    away_raw = american_odds_to_implied_prob(away_odds)
    if home_raw is None or away_raw is None:
        return None, None

    total = home_raw + away_raw
    if total <= 0:
        return None, None

    return home_raw / total, away_raw / total