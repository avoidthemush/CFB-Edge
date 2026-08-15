"""
Filters existing training/holdout CSVs down to FBS-vs-FBS games only.
No regeneration needed - the full feature data already exists, this
just removes rows involving a non-FBS opponent. Original CSVs are left
untouched, in case we want to compare or revert.
"""
import pandas as pd
from app.db import SessionLocal
from app.models import Game, Team

db = SessionLocal()
fbs_ids = {t.id for t in db.query(Team).filter(Team.division == "fbs").all()}

games = db.query(Game.id, Game.home_team_id, Game.away_team_id).all()
fbs_game_ids = {
    g.id for g in games
    if g.home_team_id in fbs_ids and g.away_team_id in fbs_ids
}
db.close()

for input_path, output_path in [
    ("training_data_validation_v2.csv", "training_data_validation_v2_fbs.csv"),
    ("training_data_2025_holdout_v2.csv", "training_data_2025_holdout_v2_fbs.csv"),
]:
    df = pd.read_csv(input_path)
    before = len(df)
    df_filtered = df[df["game_id"].isin(fbs_game_ids)]
    df_filtered.to_csv(output_path, index=False)
    print(f"{input_path}: {before} -> {len(df_filtered)} rows -> {output_path}")