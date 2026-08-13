import csv
from collections import Counter

with open("training_data_validation.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows: {len(rows)}")

print("\n=== Rows per season ===")
season_counts = Counter(r["season"] for r in rows)
for season in sorted(season_counts):
    print(f"  {season}: {season_counts[season]}")

print("\n=== Null/empty rate for key columns ===")
key_fields = [
    "diff_sp+_rating", "diff_elo_rating", "diff_off_ppa", "diff_def_ppa",
    "diff_talent_score", "diff_off_returning_ppa_pct", "diff_def_returning_havoc_pct",
    "market_spread", "market_total", "actual_spread", "actual_total", "home_won",
]
for field in key_fields:
    empty = sum(1 for r in rows if r.get(field) in (None, "", "None"))
    print(f"  {field}: {empty}/{len(rows)} empty ({empty/len(rows)*100:.1f}%)")

print("\n=== Sanity ranges ===")
spreads = [float(r["actual_spread"]) for r in rows if r["actual_spread"] not in (None, "", "None")]
totals = [float(r["actual_total"]) for r in rows if r["actual_total"] not in (None, "", "None")]
print(f"  actual_spread: min={min(spreads)}, max={max(spreads)}, avg={sum(spreads)/len(spreads):.1f}")
print(f"  actual_total: min={min(totals)}, max={max(totals)}, avg={sum(totals)/len(totals):.1f}")

market_spreads = [float(r["market_spread"]) for r in rows if r["market_spread"] not in (None, "", "None")]
print(f"  market_spread coverage: {len(market_spreads)}/{len(rows)} ({len(market_spreads)/len(rows)*100:.1f}%)")

print("\n=== Sample row ===")
print(rows[0])