import pandas as pd
import hashlib

files = ["training_data_validation_v2_fbs.csv", "training_data_2025_holdout_v2_fbs.csv"]

for f in files:
    try:
        df = pd.read_csv(f)
        with open(f, "rb") as fh:
            md5 = hashlib.md5(fh.read()).hexdigest()
        print(f"{f}:")
        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        print(f"  Seasons present: {sorted(df['season'].unique())}")
        print(f"  MD5: {md5}")
        print(f"  Any fully-null rows: {df.isnull().all(axis=1).sum()}")
    except Exception as e:
        print(f"{f}: FAILED TO READ - {e}")
    print()