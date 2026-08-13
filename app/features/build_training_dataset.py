"""
Generates the full feature+target dataset for a year range, one row per
completed game. Used to build both the validation set (2021-2024) and,
later, the production set (2021-2025).
"""
import csv
import time
from app.db import SessionLocal
from app.models import Game
from app.features.build_game_features import build_game_features


def build_dataset(start_year: int, end_year: int, output_path: str):
    db = SessionLocal()

    games = db.query(Game).filter(
        Game.season >= start_year, Game.season <= end_year,
        Game.completed == True,
    ).order_by(Game.season, Game.week).all()

    print(f"Building features for {len(games)} completed games ({start_year}-{end_year})...")

    rows = []
    failed = 0
    start_time = time.time()

    for i, game in enumerate(games):
        try:
            features = build_game_features(game.id, db=db)
            if features:
                rows.append(features)
        except Exception as e:
            failed += 1

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            print(f"  ...{i + 1}/{len(games)} processed ({elapsed:.0f}s elapsed)")

    db.close()

    if not rows:
        print("No rows generated - aborting write")
        return

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {output_path} ({failed} failed)")


if __name__ == "__main__":
    build_dataset(2021, 2024, "training_data_validation.csv")