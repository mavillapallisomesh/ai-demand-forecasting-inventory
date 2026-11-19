"""Feature engineering for the daily demand series.

Builds a modelling frame from daily_sales with lag / rolling / calendar
features for the XGBoost model, and returns the plain daily series for ARIMA.
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import DUCKDB_PATH  # noqa: E402


def load_daily_series() -> pd.DataFrame:
    """Daily total quantity sold, one row per calendar day, date-sorted."""
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        df = con.execute(
            "SELECT sale_date, total_quantity, total_revenue, n_orders "
            "FROM daily_sales ORDER BY sale_date"
        ).fetch_df()
    finally:
        con.close()
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df.set_index("sale_date").asfreq("D")  # fills any missing days with NaN


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag, rolling and calendar features. Rows with NaN features are kept
    here and dropped by the caller after the train/test split."""
    out = df.copy()
    y = out["total_quantity"]
    out["lag_1"] = y.shift(1)
    out["lag_2"] = y.shift(2)
    out["lag_3"] = y.shift(3)
    out["lag_7"] = y.shift(7)
    out["lag_14"] = y.shift(14)
    out["lag_21"] = y.shift(21)
    out["lag_28"] = y.shift(28)
    out["roll_mean_7"] = y.shift(1).rolling(7).mean()
    out["roll_std_7"] = y.shift(1).rolling(7).std()
    out["roll_mean_14"] = y.shift(1).rolling(14).mean()
    out["roll_mean_28"] = y.shift(1).rolling(28).mean()
    out["roll_std_28"] = y.shift(1).rolling(28).std()
    out["dow"] = out.index.dayofweek
    out["month"] = out.index.month
    out["is_weekend"] = (out.index.dayofweek >= 5).astype(int)
    out["dow_sin"] = np.sin(2 * np.pi * out.index.dayofweek / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out.index.dayofweek / 7)
    out["trend"] = np.arange(len(out))
    # Gift retailer: demand ramps into Christmas. Days to the next Dec 25,
    # clipped to [0, 60] so only the festive window carries signal.
    next_xmas = pd.to_datetime(
        [f"{d.year if d.month < 12 or d.day <= 25 else d.year + 1}-12-25"
         for d in out.index])
    out["days_to_christmas"] = np.clip((next_xmas - out.index).days, 0, 60)
    return out


FEATURE_COLUMNS = [
    "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_21", "lag_28",
    "roll_mean_7", "roll_std_7", "roll_mean_14", "roll_mean_28", "roll_std_28",
    "dow", "month", "is_weekend", "dow_sin", "dow_cos", "trend",
    "days_to_christmas",
]
