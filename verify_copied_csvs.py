import hashlib
import pandas as pd

def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

for filename in ["training_data_validation_v2_fbs.csv", "training_data_2025_holdout_v2_fbs.csv"]:
    df = pd.read_csv(filename)
    print(f"{filename}:")
    print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
    print(f"  Seasons present: {sorted(df['season'].unique().tolist())}")
    print(f"  MD5: {file_hash(filename)}")
    print(f"  Any fully-null rows: {df.isnull().all(axis=1).sum()}")
    print()