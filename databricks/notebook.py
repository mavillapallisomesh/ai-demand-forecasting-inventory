# Databricks notebook source
# AI Demand Forecasting & Inventory Optimization — Databricks port
#
# This file mirrors the local pipeline (src/ + sql/) for Databricks.
# Import it into a Databricks workspace (Workspace > Import > File) and attach
# it to a cluster with the repo's requirements.txt installed.
# The SQL cells below are the same queries as sql/01_staging.sql etc.,
# adapted to a Unity Catalog volume path for the raw file.

# COMMAND ----------
# MAGIC %md
# MAGIC # 1. Ingest — load Online Retail II into a Delta table
# MAGIC Raw file: `/Volumes/<catalog>/<schema>/raw/online_retail_II.csv`
# MAGIC (UCI Online Retail II, CC BY 4.0). The local pipeline uses DuckDB;
# MAGIC the SQL is written to move across with minimal change.

# COMMAND ----------
# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE raw_online_retail
# MAGIC USING CSV
# MAGIC OPTIONS (header 'true', inferSchema 'true')
# MAGIC LOCATION '/Volumes/<catalog>/<schema>/raw/online_retail_II.csv';

# COMMAND ----------
# MAGIC %md
# MAGIC # 2. SQL transforms (same logic as sql/01_staging.sql, sql/02_daily_sales.sql, sql/03_sku_stats.sql)
# MAGIC Run each file as a Databricks SQL query, or paste the contents here.
# MAGIC Spark SQL notes: `strptime` -> `to_timestamp(InvoiceDate, 'MM/dd/yyyy HH:mm')`;
# MAGIC `STDDEV_SAMP` is supported as `stddev_samp`.

# COMMAND ----------
# MAGIC %sql
# MAGIC -- staging (adapted from sql/01_staging.sql)
# MAGIC CREATE OR REPLACE TABLE stg_online_retail AS
# MAGIC SELECT
# MAGIC   CAST(Invoice AS STRING) AS invoice_no,
# MAGIC   CAST(StockCode AS STRING) AS stock_code,
# MAGIC   CAST(Description AS STRING) AS description,
# MAGIC   CAST(Quantity AS INT) AS quantity,
# MAGIC   to_timestamp(InvoiceDate, 'MM/dd/yyyy HH:mm') AS invoice_ts,
# MAGIC   CAST(Price AS DOUBLE) AS unit_price,
# MAGIC   CAST(`Customer ID` AS INT) AS customer_id,
# MAGIC   CAST(Country AS STRING) AS country,
# MAGIC   CAST(Quantity AS DOUBLE) * CAST(Price AS DOUBLE) AS line_revenue
# MAGIC FROM raw_online_retail
# MAGIC WHERE Invoice IS NOT NULL
# MAGIC   AND NOT startswith(CAST(Invoice AS STRING), 'C')
# MAGIC   AND CAST(Quantity AS INT) > 0
# MAGIC   AND CAST(Price AS DOUBLE) > 0
# MAGIC   AND StockCode IS NOT NULL
# MAGIC   AND Description IS NOT NULL;

# COMMAND ----------
# MAGIC %md
# MAGIC # 3. Train & track with MLflow (same code as src/train.py)
# MAGIC MLflow is native on Databricks — `mlflow.set_experiment` points at the
# MAGIC workspace experiment instead of the local `file://mlruns` store.
# MAGIC Run `%run ./src/train` (import the repo) or copy src/train.py in.

# COMMAND ----------
# MAGIC %md
# MAGIC # 4. Inventory plan (src/inventory.py) and dashboard export
# MAGIC Safety stock = z·σ·√LT, reorder point = mean·LT + safety stock.
# MAGIC Export the plan tables to Power BI via the Databricks Power BI
# MAGIC connector, or write them to `powerbi/dataset/` as in the local run.
