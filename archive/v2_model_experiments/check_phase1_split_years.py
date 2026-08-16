import pandas as pd

df = pd.read_csv("training_data_validation_v2_fbs.csv")
df = df[df["season"] <= 2022]

for year in [2019, 2020, 2021, 2022]:
    year_df = df[df["season"] == year]
    has_open = year_df["market_spread_open"].notna().sum()
    total = len(year_df)
    print(f"{year}: {total} total games, {has_open} with market_spread_open ({has_open/total*100:.0f}%)")