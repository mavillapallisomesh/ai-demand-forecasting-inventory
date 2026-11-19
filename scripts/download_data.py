"""Download the UCI Online Retail II dataset (free, no account needed).

Primary source: UCI Machine Learning Repository, dataset 502, CC BY 4.0
(Chen, D. 2012, https://doi.org/10.24432/C5CG6D).
The workbook has two sheets (Year 2009-2010 and Year 2010-2011, 1,067,371 rows
in total). Some networks block archive.ics.uci.edu, so this script falls back
to a public GitHub mirror of the same data (the Year 2009-2010 sheet as CSV,
525,461 rows) hosted in the Packt "The Data Analysis Workshop" repo.

Usage:
    python scripts/download_data.py [--force]
"""
import argparse
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import CSV_MIRROR_URL, RAW_CSV, RAW_XLSX, UCI_XLSX_URL, UCI_XLSX_URL_LEGACY


def _fetch(url: str, dest: Path, timeout: int = 180) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download even if files exist")
    args = parser.parse_args()

    if RAW_CSV.exists() and not args.force:
        print(f"Raw CSV already present: {RAW_CSV} ({RAW_CSV.stat().st_size:,} bytes)")
        return 0
    if RAW_XLSX.exists() and not args.force:
        print(f"Raw XLSX already present: {RAW_XLSX} ({RAW_XLSX.stat().st_size:,} bytes)")
        return 0

    for url, dest in [
        (UCI_XLSX_URL, RAW_XLSX),
        (UCI_XLSX_URL_LEGACY, RAW_XLSX),
        (CSV_MIRROR_URL, RAW_CSV),
    ]:
        try:
            size = _fetch(url, dest)
            print(f"Downloaded {url}\n  -> {dest} ({size:,} bytes)")
            return 0
        except Exception as exc:  # noqa: BLE001 - try next source
            print(f"FAILED {url}: {type(exc).__name__}: {exc}")

    print("ERROR: all download sources failed. See README.md for manual steps.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
