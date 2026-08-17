"""
Trains and saves Total's production artifacts - NOT sklearn models like
Spread. Each approved system is a bucket-lookup table: deciles of a
factor (pace, field position, travel, wind), each with a known average
market_total_open from the baseline season. "Training" = computing and
saving these lookup tables from the most recent complete season (2025).

IMPORTANT DEVIATION FROM BACKTESTING: during validation, "extreme
deviation" (top/bottom X%) was measured against the TEST year's own
deviation distribution. For live prediction, we don't have a full 2026
season of deviations yet. This production version instead fixes the
extreme-deviation cutoffs using the BASELINE (2025) season's own
deviation distribystem, applied going forward - a reasonable adaptation,
but not identical to the backtest methodology. Re-run this script each
year once the new season completes, to roll the baseline forward.
"""
import json
import pandas as pd

BASELINE_YEAR = 2025  # most recent complete season - re-run yearly to roll forward

SYSTEMS = {
    "pace_deviation": {
        "dimension": lambda df: df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"],
        "percentile": 0.15,
        "filter": None,
    },
    "field_position_deviation": {
        "dimension": lambda df: df["home_off_field_position_predicted_points"] + df["away_off_field_position_predicted_points"],
        "percentile": 0.075,
        "filter": None,
    },
    "travel_deviation": {
        "dimension": lambda df: df["home_travel_distance"].fillna(0) + df["away_travel_distance"].fillna(0),
        "percentile": 0.05,
        "filter": None,
    },
    "wind_deviation": {
        "dimension": lambda df: df["wind_mph"],
        "percentile": 0.075,
        "filter": lambda df: df["market_spread_open"] < 0,  # favorite_home
    },
    "pace_deviation_home_favorite_tag": {
        "dimension": lambda df: df["home_off_plays_per_drive"] + df["away_off_plays_per_drive"],
        "percentile": 0.15,
        "filter": lambda df: df["market_spread_open"] < 0,
    },
}


def build_system(df, config):
    df = df.copy()
    df["bucket_val"] = config["dimension"](df)
    df = df.dropna(subset=["bucket_val"])

    df["decile"], bins = pd.qcut(df["bucket_val"], 10, labels=False, duplicates="drop", retbins=True)
    bucket_avg = df.groupby("decile")["market_total_open"].mean()

    df["expected_total"] = df["decile"].map(bucket_avg)
    df["deviation"] = df["market_total_open"] - df["expected_total"]

    filtered = df[config["filter"](df)] if config["filter"] else df
    low_cutoff = float(filtered["deviation"].quantile(config["percentile"]))
    high_cutoff = float(filtered["deviation"].quantile(1 - config["percentile"]))

    return {
        "bins": bins.tolist(),
        "bucket_avg": {str(int(k)): float(v) for k, v in bucket_avg.items()},
        "low_cutoff": low_cutoff,
        "high_cutoff": high_cutoff,
        "baseline_year": BASELINE_YEAR,
        "n_games": len(df),
    }


def train_production_total():
    full_df = pd.read_csv("training_data_validation_v2_fbs.csv")
    full_df_2025 = pd.read_csv("training_data_2025_holdout_v2_fbs.csv")
    full_df = pd.concat([full_df, full_df_2025], ignore_index=True)
    full_df = full_df[full_df["market_total_open"].notna() & full_df["actual_total"].notna()]

    baseline_df = full_df[full_df["season"] == BASELINE_YEAR]
    print(f"Building production artifacts from {BASELINE_YEAR} season ({len(baseline_df)} games)\n")

    artifacts = {}
    for name, config in SYSTEMS.items():
        artifacts[name] = build_system(baseline_df, config)
        print(f"  {name}: {artifacts[name]['n_games']} games, "
              f"cutoffs [{artifacts[name]['low_cutoff']:.2f}, {artifacts[name]['high_cutoff']:.2f}]")

    with open("total_production_systems.json", "w") as f:
        json.dump(artifacts, f, indent=2)

    print(f"\nSaved: total_production_systems.json ({len(artifacts)} systems)")
    print("Systems: Pace Deviation, Field Position Deviation, Travel Deviation, "
          "Wind Deviation (home-favorite only), Home Favorite tag (on Pace Deviation)")
    print("\nRE-RUN THIS SCRIPT after each season completes to roll the baseline forward.")


if __name__ == "__main__":
    train_production_total()