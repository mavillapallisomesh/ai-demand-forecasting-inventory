"""Run the full pipeline end to end.

    python -m src.run_pipeline [--rebuild] [--lead-time-days 7] [--no-mlflow]

Steps: ingest (SQL transforms) -> data-quality checks -> train/compare
(MLflow) -> inventory plan -> Plotly dashboard -> Power BI export files.
Data-quality errors stop the run; warnings are reported.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import PROJECT_ROOT  # noqa: E402


def run_step(name: str, argv: list[str]) -> None:
    print(f"\n=== {name} ===")
    proc = subprocess.run([sys.executable, "-m", *argv],
                          cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        print(f"FAILED: {name} (exit {proc.returncode})")
        raise SystemExit(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--lead-time-days", type=int, default=7)
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    ingest = ["src.ingest"] + (["--rebuild"] if args.rebuild else [])
    run_step("1/5 ingest + SQL transforms", ingest)
    run_step("2/5 data-quality checks", ["src.data_quality"])
    train = ["src.train"] + (["--no-mlflow"] if args.no_mlflow else [])
    run_step("3/5 train + compare (Naive / ARIMA / XGBoost)", train)
    run_step("4/5 safety stock + reorder points",
             ["src.inventory", "--lead-time-days", str(args.lead_time_days)])
    run_step("5/5 Plotly dashboard", ["src.dashboard"])
    run_step("5b/5 Power BI export files", ["src.export_powerbi"])

    print("\nPipeline complete. Key outputs in outputs/:")
    for f in ["model_comparison.json", "inventory_summary.json",
              "test_predictions.csv", "forecast_14d.csv",
              "inventory_plan.csv", "lead_time_whatif.csv", "dashboard.html",
              "xgboost_model.json"]:
        print(f"  - outputs/{f}")
    print("Power BI inputs in powerbi/dataset/ (see powerbi/README.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
