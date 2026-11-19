-- 01_staging.sql — Load the raw Online Retail II CSV into DuckDB and clean it.
-- Run via src/ingest.py (DuckDB executes these statements in order).
-- Cleaning rules (documented, reversible — nothing is deleted from raw):
--   * drop cancelled invoices (InvoiceNo starting with 'C')
--   * drop lines with Quantity <= 0 or UnitPrice <= 0
--   * drop lines with a missing StockCode / Description
--   * derive line_revenue = Quantity * UnitPrice
--   * parse InvoiceDate to TIMESTAMP

CREATE OR REPLACE TABLE raw_online_retail AS
SELECT *
FROM read_csv_auto(
    'data/raw/online_retail_II.csv',
    header = true,
    ignore_errors = true
);

CREATE OR REPLACE TABLE stg_online_retail AS
SELECT
    CAST("Invoice" AS VARCHAR) AS invoice_no,
    CAST("StockCode" AS VARCHAR) AS stock_code,
    CAST("Description" AS VARCHAR) AS description,
    CAST("Quantity" AS INTEGER) AS quantity,
    CAST(strptime("InvoiceDate", '%d/%m/%Y %H:%M') AS TIMESTAMP) AS invoice_ts,
    CAST("Price" AS DOUBLE) AS unit_price,
    CAST("Customer ID" AS INTEGER) AS customer_id,
    CAST("Country" AS VARCHAR) AS country,
    CAST("Quantity" AS DOUBLE) * CAST("Price" AS DOUBLE) AS line_revenue
FROM raw_online_retail
WHERE "Invoice" IS NOT NULL
  AND NOT starts_with(CAST("Invoice" AS VARCHAR), 'C')
  AND CAST("Quantity" AS INTEGER) > 0
  AND CAST("Price" AS DOUBLE) > 0
  AND "StockCode" IS NOT NULL
  AND "Description" IS NOT NULL;
