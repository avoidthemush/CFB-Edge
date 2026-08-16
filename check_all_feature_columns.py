"""
Full audit of every column currently in our feature CSVs, so we can see
exactly what exists vs. what's missing before deciding what's worth a
regeneration - not guessing or dropping things for speed.
"""
import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")

print(f"Total columns: {len(df.columns)}\n")

categories = {
    "identifiers/target": [],
    "ratings": [],
    "offense_raw": [],
    "defense_raw": [],
    "matchups": [],
    "returning_production": [],
    "coach": [],
    "recruiting_talent": [],
    "weather": [],
    "pace": [],
    "recent_form": [],
    "market": [],
    "context_flags": [],
    "uncategorized": [],
}

for col in df.columns:
    lc = col.lower()
    if col in ["game_id", "season", "week", "actual_spread", "actual_total", "home_won"]:
        categories["identifiers/target"].append(col)
    elif "rating" in lc:
        categories["ratings"].append(col)
    elif "matchup" in lc:
        categories["matchups"].append(col)
    elif "returning" in lc:
        categories["returning_production"].append(col)
    elif "coach" in lc:
        categories["coach"].append(col)
    elif "recruiting" in lc or "talent" in lc:
        categories["recruiting_talent"].append(col)
    elif any(w in lc for w in ["temp_f", "wind", "precip"]):
        categories["weather"].append(col)
    elif "plays_per_drive" in lc:
        categories["pace"].append(col)
    elif "last_game" in lc or "days_since" in lc:
        categories["recent_form"].append(col)
    elif "market" in lc or "provider" in lc:
        categories["market"].append(col)
    elif any(w in lc for w in ["neutral", "dome"]):
        categories["context_flags"].append(col)
    elif lc.startswith("home_def") or lc.startswith("away_def") or lc.startswith("diff_def"):
        categories["defense_raw"].append(col)
    elif lc.startswith("home_off") or lc.startswith("away_off") or lc.startswith("diff_off"):
        categories["offense_raw"].append(col)
    else:
        categories["uncategorized"].append(col)

for cat, cols in categories.items():
    print(f"=== {cat} ({len(cols)}) ===")
    for c in sorted(cols):
        print(f"  {c}")
    print()