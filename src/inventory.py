"""Safety stock, reorder points and stockout-risk flagging.

Method (classic inventory theory, documented assumptions):
  safety_stock = z * sigma_daily * sqrt(lead_time_days)
  reorder_point = mean_daily_demand * lead_time_days + safety_stock

Inputs:
  - per-SKU demand stats from sql/03_sku_stats.sql (90-day window)
  - the 14-day aggregate forecast from src/train.py, allocated to SKUs by
    each SKU's share of the last 28 days of demand (the UCI data has no
    per-SKU forecast target with enough history for every SKU, and no
    on-hand inventory or supplier lead-time columns — lead time is a
    configurable parameter, default 7 days).

A SKU is flagged HIGH stockout risk when its forecast demand over the lead
time exceeds its reorder point (i.e. even ordering at the ROP would not cover
expected demand), or when its demand is extremely volatile (CV above the 90th
percentile of scored SKUs) and its forecast is rising vs its recent average.
A fixed CV cutoff is not used: daily SKU demand in this data is intermittent
(median CV is ~1.9), so CV > 1.0 would flag most of the catalogue and the flag
would carry no signal.

Usage:
    python -m src.inventory [--lead-time-days 7]
"""
import argparse
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import (  # noqa: E402
    DEFAULT_LEAD_TIME_DAYS, DUCKDB_PATH, FORECAST_HORIZON_DAYS,
    LEAD_TIME_WHATIF_DAYS, MIN_SKU_HISTORY_DAYS, OUTPUTS,
    SERVICE_LEVEL_Z, STATS_WINDOW_DAYS,
)


def load_sku_stats() -> pd.DataFrame:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        stats = con.execute("SELECT * FROM sku_stats").fetch_df()
        share = con.execute(
            "SELECT stock_code, SUM(quantity) AS qty_28d FROM sku_daily "
            "WHERE sale_date > (SELECT MAX(sale_date) FROM daily_sales) - INTERVAL 28 DAY "
            "GROUP BY 1"
        ).fetch_df()
    finally:
        con.close()
    df = stats.merge(share, on="stock_code", how="left")
    df["qty_28d"] = df["qty_28d"].fillna(0)
    return df


def compute_plan(stats: pd.DataFrame, forecast_total_14d: float,
                 lead_time_days: int) -> pd.DataFrame:
    """Return one row per scored SKU with SS, ROP and risk flags."""
    import numpy as np

    df = stats.copy()
    df = df[(df["n_active_days"] >= MIN_SKU_HISTORY_DAYS)
            & (df["mean_daily_demand"] > 0)].copy()
    total_28d = df["qty_28d"].sum()
    df["share_28d"] = df["qty_28d"] / total_28d if total_28d else 0
    # Allocate the aggregate forecast proportionally to recent demand share.
    df["forecast_lt_demand"] = (
        forecast_total_14d * (lead_time_days / FORECAST_HORIZON_DAYS)
        * df["share_28d"])
    df["std_daily_demand"] = df["std_daily_demand"].fillna(0)
    z = SERVICE_LEVEL_Z
    df["safety_stock"] = z * df["std_daily_demand"] * np.sqrt(lead_time_days)
    df["reorder_point"] = (df["mean_daily_demand"] * lead_time_days
                           + df["safety_stock"])
    df["lead_time_demand"] = df["mean_daily_demand"] * lead_time_days
    df["days_of_cover"] = df["reorder_point"] / df["mean_daily_demand"]
    df["forecast_vs_rop"] = df["forecast_lt_demand"] / df["reorder_point"]
    df["forecast_rising"] = (
        df["forecast_lt_demand"] > df["lead_time_demand"] * 1.10)
    # Volatility cutoff is data-driven (90th percentile of CV): a fixed CV > 1
    # is meaningless for intermittent retail demand (median CV here is ~1.9).
    cv_cutoff = float(df["cv_demand"].quantile(0.90))
    df["high_stockout_risk"] = (
        (df["forecast_lt_demand"] > df["reorder_point"])
        | ((df["cv_demand"] > cv_cutoff) & df["forecast_rising"])
    )
    return df.sort_values("forecast_lt_demand", ascending=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lead-time-days", type=int, default=DEFAULT_LEAD_TIME_DAYS)
    args = parser.parse_args()

    forecast = pd.read_csv(OUTPUTS / "forecast_14d.csv")
    forecast_total_14d = float(forecast["forecast_quantity"].sum())
    print(f"14-day aggregate forecast total: {forecast_total_14d:,.0f} units")

    stats = load_sku_stats()
    plan = compute_plan(stats, forecast_total_14d, args.lead_time_days)

    # Lead-time what-if: recompute flagged counts for each lead time.
    whatif = []
    for lt in LEAD_TIME_WHATIF_DAYS:
        p = compute_plan(stats, forecast_total_14d, lt)
        whatif.append({
            "lead_time_days": lt,
            "skus_scored": len(p),
            "high_risk_skus": int(p["high_stockout_risk"].sum()),
            "total_safety_stock_units": float(p["safety_stock"].sum()),
            "total_reorder_point_units": float(p["reorder_point"].sum()),
        })
    whatif_df = pd.DataFrame(whatif)

    n_risk = int(plan["high_stockout_risk"].sum())
    print(f"SKUs scored: {len(plan):,} | high stockout risk: {n_risk:,}")
    print(f"Total safety stock: {plan['safety_stock'].sum():,.0f} units | "
          f"total ROP: {plan['reorder_point'].sum():,.0f} units")

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    plan.to_csv(OUTPUTS / "inventory_plan.csv", index=False)
    whatif_df.to_csv(OUTPUTS / "lead_time_whatif.csv", index=False)
    summary = {
        "lead_time_days": args.lead_time_days,
        "service_level_z": SERVICE_LEVEL_Z,
        "stats_window_days": STATS_WINDOW_DAYS,
        "skus_scored": len(plan),
        "high_stockout_risk_skus": n_risk,
        "total_safety_stock_units": float(plan["safety_stock"].sum()),
        "total_reorder_point_units": float(plan["reorder_point"].sum()),
        "whatif": whatif,
    }
    (OUTPUTS / "inventory_summary.json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
