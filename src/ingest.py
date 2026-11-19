"""Ingest: load the raw CSV into DuckDB and run the SQL transforms.

Usage:
    python -m src.ingest [--rebuild]
"""
import argparse
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import DATA_PROCESSED, DUCKDB_PATH, PROJECT_ROOT, RAW_CSV, RAW_XLSX  # noqa: E402


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    sql = path.read_text()
    # DuckDB cannot run the read_csv_auto path relative to CWD reliably when the
    # connection is opened elsewhere, so run from the project root.
    con.execute(sql)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="delete the DuckDB file first")
    args = parser.parse_args()

    if not RAW_CSV.exists() and not RAW_XLSX.exists():
        print("ERROR: no raw data found. Run: python scripts/download_data.py")
        return 1
    if RAW_XLSX.exists() and not RAW_CSV.exists():
        print("NOTE: only the XLSX is present — convert it to CSV first "
              "(see README.md). This run uses the CSV.")
        return 1

    if args.rebuild and DUCKDB_PATH.exists():
        DUCKDB_PATH.unlink()

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        for name in ["01_staging.sql", "02_daily_sales.sql", "03_sku_stats.sql"]:
            print(f"Running sql/{name} ...")
            run_sql_file(con, PROJECT_ROOT / "sql" / name)
        raw_n = con.execute("SELECT COUNT(*) FROM raw_online_retail").fetchone()[0]
        clean_n = con.execute("SELECT COUNT(*) FROM stg_online_retail").fetchone()[0]
        days = con.execute("SELECT COUNT(*) FROM daily_sales").fetchone()[0]
        skus = con.execute("SELECT COUNT(DISTINCT stock_code) FROM sku_daily").fetchone()[0]
        print(f"raw rows: {raw_n:,} | cleaned rows: {clean_n:,} | "
              f"days: {days} | SKUs: {skus:,}")
    finally:
        con.close()
    print(f"DuckDB written to {DUCKDB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
