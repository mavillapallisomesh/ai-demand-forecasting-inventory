# Scheduling — weekly retraining

The pipeline is designed to be re-run on a schedule so forecasts and safety
stocks stay fresh as new sales land.

## Cron (Linux / macOS)

```cron
# Every Sunday at 02:00 UTC — full retrain + dashboard refresh
0 2 * * 0 /path/to/ai-demand-forecasting-inventory/scripts/retrain_weekly.sh >> /path/to/ai-demand-forecasting-inventory/outputs/retrain.log 2>&1
```

`scripts/retrain_weekly.sh` activates the project virtualenv and runs
`python -m src.run_pipeline`, which re-ingests, re-checks data quality,
re-trains all three models, recomputes safety stock / reorder points and
regenerates the dashboard and Power BI export files. MLflow logs each run
under the `ai-demand-forecasting-inventory` experiment, so model drift
(MAPE/RMSE over time) is visible in the MLflow UI:

```bash
.venv/bin/mlflow ui --backend-store-uri file://$PWD/mlruns
```

## Databricks / Azure

On Databricks, schedule the same steps as a Jobs workflow (see
`databricks/`): one task per pipeline step, weekly trigger, with the SQL
transforms running as Databricks SQL against the same `sql/` files. The
local DuckDB implementation is intentionally SQL-first so the queries move
across with minimal change.
