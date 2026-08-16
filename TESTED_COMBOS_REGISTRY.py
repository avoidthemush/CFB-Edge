"""
Registry of every distinct (feature-categories, rule-set) combination
already tested for Spread, so we never accidentally re-run the same
thing twice. Check TESTED before running a new test; add to it after.
Not imported by other scripts (kept simple, human-readable) - checked
manually before designing each new test.
"""

TESTED = [
    # (label, categories_used, rules_used, result_summary)
    ("Full feature set (incl. recruiting)", "all 10 categories", "confidence>=0.60", "2/4 years, discarded"),
    ("Original Mid-Season Value Dog", "all except recruiting", "week>=5, underdog, non-neutral, conf>=0.60", "3/4 years, p=0.1463, under the bar"),
    ("Candidate A", "returning_qb, returning_production, raw_offense_defense_stats", "confidence>=0.60", "APPROVED - 55.3% pooled"),
    ("Candidate B", "returning_qb, returning_production, coach_quality, weather, recent_form", "confidence>=0.60", "discarded - failed 2025"),
    ("Focused Value", "returning_qb, returning_production, raw_offense_defense_stats", "week>=5, underdog, non-neutral, conf>=0.60", "APPROVED - 60.8% pooled"),
    ("21 individual pairs", "base + every 2-category combo", "confidence>=0.60", "0/21 beat baseline"),
    ("Stepwise individual-feature (2024-val)", "~85 individual features, algorithmic", "confidence>=0.60", "discarded - overfit"),
    ("Stepwise individual-feature (2023-val)", "~85 individual features, algorithmic", "confidence>=0.60", "discarded - overfit, no overlap w/ 2024 run"),
    ("Variable-size search sizes 1-6, 15-bet floor", "all 12 categories, all combos size 1-6", "confidence>=0.60", "discarded - tiny samples, noise"),
    ("Variable-size search sizes 1-6, 100-bet floor", "all 12 categories, all combos size 1-6", "confidence>=0.60", "Candidate A reappeared as best size-3; nothing else cleared recruiting-free + 100-bet bar convincingly"),
    ("Coach experience gap standalone rule", "diff_coach_experience_seasons only, no model", "gap>=3/5/8 years", "discarded - all below breakeven, no trend"),
    ("Large underdog segment (Candidate A base)", "returning_qb, returning_production, raw_offense_defense_stats", "conf>=0.60, underdog, spread-size segmented", "PROMISING - monotonic 55.9%/57.1%/57.4% by dog size, testing large-dogs-only next"),
    ("Large underdog angle (Candidate A + spread>=14)", "returning_qb, returning_production, raw_offense_defense_stats", "conf>=0.60, underdog, spread_open>=14", "NOT APPROVED - 56.8% pooled but only 132 bets, p=0.1765, bootstrap 83.6% (below 90% floor), 2025 exactly at breakeven (n=10, too thin to trust). Real hypothesis, insufficient sample - revisit with more data."),
]

# NEW, NOT YET TESTED - queue for upcoming work
QUEUED = [
    "Coach experience gap as standalone rule (not model-embedded)",
    "Large underdog (double-digit spread) segment, using Candidate A's existing predictions",
    "Rolling in-season ATS streak - REQUIRES NEW FEATURE BUILD, not just a new test",
    "Tough-loss-coming-off (large negative last_game_margin) as standalone segment",
    "Travel distance + short-week-after-travel fatigue - feature built, not yet wired into pipeline or tested",
]