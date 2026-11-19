"""Automated data-quality checks.

Runs a battery of checks against the DuckDB warehouse and writes a JSON
report to outputs/data_quality_report.json. Each check has a severity:
'error' fails the pipeline (exit code 1), 'warning' is reported but does not
block. Thresholds live in CHECKS so they are easy to tune.

Usage:
    python -m src.data_quality [--strict]
"""
import argparse
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import DUCKDB_PATH, OUTPUTS  # noqa: E402

CHECKS = [
    # (name, sql, severity, fail_condition lambda value: bool)
    ("raw_rows_present",
     "SELECT COUNT(*) FROM raw_online_retail", "error", lambda v: v == 0),
    ("cleaned_rows_present",
     "SELECT COUNT(*) FROM stg_online_retail", "error", lambda v: v == 0),
    ("no_negative_quantity",
     "SELECT COUNT(*) FROM stg_online_retail WHERE quantity <= 0", "error", lambda v: v > 0),
    ("no_negative_price",
     "SELECT COUNT(*) FROM stg_online_retail WHERE unit_price <= 0", "error", lambda v: v > 0),
    ("no_null_stock_code",
     "SELECT COUNT(*) FROM stg_online_retail WHERE stock_code IS NULL", "error", lambda v: v > 0),
    ("no_null_invoice_date",
     "SELECT COUNT(*) FROM stg_online_retail WHERE invoice_ts IS NULL", "error", lambda v: v > 0),
    ("no_cancelled_invoices_leaked",
     "SELECT COUNT(*) FROM stg_online_retail WHERE invoice_no LIKE 'C%'", "error", lambda v: v > 0),
    ("no_duplicate_lines",
     "SELECT COUNT(*) - COUNT(DISTINCT (invoice_no, stock_code, quantity, unit_price, invoice_ts)) "
     "FROM stg_online_retail", "warning", lambda v: v > 0),
    ("no_future_dates",
     "SELECT COUNT(*) FROM stg_online_retail WHERE invoice_ts > CURRENT_TIMESTAMP",
     "error", lambda v: v > 0),
    ("daily_series_has_no_gaps",
     "SELECT (MAX(sale_date) - MIN(sale_date)) + 1 - COUNT(*) FROM daily_sales",
     "warning", lambda v: v > 0),
    ("missing_customer_id_share_pct",
     "SELECT 100.0 * SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) / COUNT(*) "
     "FROM stg_online_retail", "warning", lambda v: v > 50),
    ("absurd_unit_price_rows",
     "SELECT COUNT(*) FROM stg_online_retail WHERE unit_price > 10000",
     "warning", lambda v: v > 0),
    ("revenue_not_null",
     "SELECT COUNT(*) FROM daily_sales WHERE total_revenue IS NULL OR total_quantity IS NULL",
     "error", lambda v: v > 0),
]


def run_checks(strict: bool = False) -> dict:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    results = []
    try:
        for name, sql, severity, fail_if in CHECKS:
            value = con.execute(sql).fetchone()[0]
            value = float(value) if value is not None else None
            failed = bool(fail_if(value))
            results.append({
                "check": name,
                "severity": severity,
                "value": value,
                "status": "FAIL" if failed else "PASS",
            })
    finally:
        con.close()

    n_fail_err = sum(1 for r in results if r["status"] == "FAIL" and r["severity"] == "error")
    n_fail_warn = sum(1 for r in results if r["status"] == "FAIL" and r["severity"] == "warning")
    report = {
        "passed": n_fail_err == 0 and (n_fail_warn == 0 or not strict),
        "errors_failed": n_fail_err,
        "warnings_failed": n_fail_warn,
        "checks": results,
    }
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    (OUTPUTS / "data_quality_report.json").write_text(json.dumps(report, indent=2))
    for r in results:
        print(f"[{r['status']:<4}] ({r['severity']:<7}) {r['check']:<38} value={r['value']}")
    print(f"errors failed: {n_fail_err}, warnings failed: {n_fail_warn}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="treat failed warnings as failures too")
    args = parser.parse_args()
    report = run_checks(strict=args.strict)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
