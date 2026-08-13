import csv
from collections import Counter, defaultdict

with open("training_data_validation.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("=== Null rate for diff_sp+_rating, by season ===")
by_season = defaultdict(lambda: [0, 0])
for r in rows:
    by_season[r["season"]][1] += 1
    if r["diff_sp+_rating"] in (None, "", "None"):
        by_season[r["season"]][0] += 1
for season in sorted(by_season):
    empty, total = by_season[season]
    print(f"  {season}: {empty}/{total} ({empty/total*100:.1f}%)")

print("\n=== Null rate for diff_sp+_rating, by week (all seasons combined) ===")
by_week = defaultdict(lambda: [0, 0])
for r in rows:
    by_week[int(r["week"])][1] += 1
    if r["diff_sp+_rating"] in (None, "", "None"):
        by_week[int(r["week"])][0] += 1
for week in sorted(by_week):
    empty, total = by_week[week]
    print(f"  Week {week}: {empty}/{total} ({empty/total*100:.1f}%)")

print("\n=== Compare null rates across rating systems, 2023 only (should have full prior-year data) ===")
rows_2023 = [r for r in rows if r["season"] == "2023"]
for field in ["diff_sp+_rating", "diff_srs_rating", "diff_fpi_rating", "diff_elo_rating"]:
    empty = sum(1 for r in rows_2023 if r[field] in (None, "", "None"))
    print(f"  {field}: {empty}/{len(rows_2023)} ({empty/len(rows_2023)*100:.1f}%)")