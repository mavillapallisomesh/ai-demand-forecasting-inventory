-- 02_daily_sales.sql — Aggregate cleaned transactions to daily grain.
-- Two tables:
--   daily_sales : one row per calendar day (all SKUs) — the forecasting target.
--   sku_daily   : one row per SKU per day — the inventory-planning grain.

CREATE OR REPLACE TABLE daily_sales AS
SELECT
    CAST(invoice_ts AS DATE) AS sale_date,
    SUM(quantity) AS total_quantity,
    SUM(line_revenue) AS total_revenue,
    COUNT(DISTINCT invoice_no) AS n_orders,
    COUNT(DISTINCT stock_code) AS n_skus,
    COUNT(*) AS n_lines
FROM stg_online_retail
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE TABLE sku_daily AS
SELECT
    CAST(invoice_ts AS DATE) AS sale_date,
    stock_code,
    MAX(description) AS description,
    SUM(quantity) AS quantity,
    SUM(line_revenue) AS revenue,
    COUNT(DISTINCT invoice_no) AS n_orders
FROM stg_online_retail
GROUP BY 1, 2
ORDER BY 1, 2;
