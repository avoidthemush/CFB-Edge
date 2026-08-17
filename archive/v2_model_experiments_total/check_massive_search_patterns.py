"""
Meta-analysis of the top 20 (and beyond) from the 9,968-combination
search - counting which underlying bucket dimensions and filters recur
most, since recurrence across many independent top results is real
signal (same lesson as Candidate A's raw_offense_defense_stats and
pace+weather), while any single result out of ~10,000 trials proves
very little on its own.
"""
from collections import Counter

# Top 20 from the actual run, transcribed for analysis
TOP_RESULTS = [
    ("1D:travel", "early_season"), ("1D:travel", "favorite_home"),
    ("1D:pace", "early_season"), ("1D:field_position", "early_season"),
    ("2D:third_down+def_success_allowed", "weeks_1_4"),
    ("1D:temp", "high_total_open"), ("1D:wind", "favorite_home"),
    ("2D:pace+def_ppa", "weeks_10_plus"), ("1D:field_position", "low_wind"),
    ("1D:field_position", "low_wind"), ("1D:def_ppa", "early_season"),
    ("1D:off_points_per_opp", "early_season"), ("1D:pace", "high_total_open"),
    ("2D:field_position+temp", "low_wind"), ("1D:field_position", "favorite_home"),
    ("1D:pace", "high_total_open"), ("1D:turnover_gap", "favorite_home"),
    ("1D:def_success_allowed", "early_season"), ("1D:travel", "low_wind"),
    ("2D:off_efficiency+def_ppa", "conference_games"),
]

bucket_counter = Counter()
filter_counter = Counter()

for bucket, filt in TOP_RESULTS:
    # Count each underlying single dimension separately, even within 2D combos
    for dim in bucket.replace("1D:", "").replace("2D:", "").split("+"):
        bucket_counter[dim] += 1
    filter_counter[filt] += 1

print("=== Underlying bucket dimensions, by recurrence in top 20 ===")
for dim, count in bucket_counter.most_common():
    print(f"  {dim}: {count}")

print("\n=== Situational filters, by recurrence in top 20 ===")
for filt, count in filter_counter.most_common():
    print(f"  {filt}: {count}")