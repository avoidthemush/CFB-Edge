"""
Converts a point margin into a win probability using the standard
normal-distribution method (margin = center of a bell curve, win
probability = area under the curve on the positive side of zero).

STDEV = 15.44, calibrated from OUR OWN data (2021-2025 FBS games,
market_spread_open vs actual_spread residuals) - not borrowed from
NFL literature (13.5-14) or an unverified CFB estimate. Confirmed
stable across all 5 years individually (15.07-15.88), and confirmed
market spreads are unbiased on average (mean residual -0.08, near zero).
"""
from scipy.stats import norm

MARGIN_STDEV = 15.44


def margin_to_win_probability(predicted_margin_for_team):
    """
    predicted_margin_for_team: positive = this team is favored by that
    many points, negative = this team is an underdog by that many points.
    Returns the probability (0-1) that this team wins outright.
    """
    return float(norm.cdf(predicted_margin_for_team / MARGIN_STDEV))


def spread_to_implied_win_probability(spread_for_team):
    """
    Convenience wrapper: given a team's own spread (negative = favored,
    positive = underdog, matching our market_spread_open convention),
    returns that team's win probability.
    """
    margin = -spread_for_team
    return margin_to_win_probability(margin)