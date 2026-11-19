"""Export the cleaned aggregates the Power BI dashboard consumes.

Writes to powerbi/dataset/ (committed, small aggregates only — no raw data):
  - daily_sales.csv       : daily totals + 14-day forecast (for accuracy views)
  - sku_forecast_inventory.csv : per-SKU demand stats, safety stock, ROP,
    forecast demand and the stockout-risk flag (for risk views)
  - lead_time_whatif.csv  : what-if table (for the lead-time slicer view)

Usage:
    python -m src.export_powerbi
"""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import DUCKDB_PATH, OUTPUTS, PROJECT_ROOT  # noqa: E402


def main() -> int:
    out_dir = PROJECT_ROOT / "powerbi" / "dataset"
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        daily = con.execute(
            "SELECT sale_date, total_quantity, total_revenue, n_orders, n_skus "
            "FROM daily_sales ORDER BY sale_date"
        ).fetch_df()
    finally:
        con.close()

    forecast = pd.read_csv(OUTPUTS / "forecast_14d.csv", parse_dates=["forecast_date"])
    fwd = forecast.rename(columns={"forecast_date": "sale_date",
                                   "forecast_quantity": "forecast_quantity"})
    daily_forecast = daily.merge(fwd, on="sale_date", how="left")

    plan = pd.read_csv(OUTPUTS / "inventory_plan.csv")
    whatif = pd.read_csv(OUTPUTS / "lead_time_whatif.csv")

    daily_forecast.to_csv(out_dir / "daily_sales.csv", index=False)
    plan.to_csv(out_dir / "sku_forecast_inventory.csv", index=False)
    whatif.to_csv(out_dir / "lead_time_whatif.csv", index=False)
    print(f"Wrote {len(daily_forecast):,} daily rows, {len(plan):,} SKU rows, "
          f"{len(whatif)} what-if rows to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
