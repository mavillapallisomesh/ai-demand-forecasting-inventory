-- 03_sku_stats.sql — Per-SKU demand statistics over the trailing window.
-- Used by the safety-stock / reorder-point calculation in src/inventory.py.
-- mean_daily_demand / std_daily_demand are computed over calendar days in the
-- window (days with no sale count as zero demand), so volatility is honest.

CREATE OR REPLACE TABLE sku_stats AS
WITH window_bounds AS (
    SELECT MAX(sale_date) AS max_date FROM daily_sales
),
calendar AS (
    SELECT CAST(d AS DATE) AS sale_date
    FROM range(
        (SELECT max_date - INTERVAL 89 DAY FROM window_bounds),
        (SELECT max_date + INTERVAL 1 DAY FROM window_bounds),
        INTERVAL 1 DAY
    ) AS t(d)
),
sku_list AS (
    SELECT DISTINCT stock_code, description FROM sku_daily
),
dense AS (
    SELECT c.sale_date, s.stock_code, s.description,
           COALESCE(d.quantity, 0) AS quantity
    FROM calendar c
    CROSS JOIN sku_list s
    LEFT JOIN sku_daily d
      ON d.sale_date = c.sale_date AND d.stock_code = s.stock_code
)
SELECT
    stock_code,
    MAX(description) AS description,
    COUNT(*) AS n_days,
    SUM(CASE WHEN quantity > 0 THEN 1 ELSE 0 END) AS n_active_days,
    AVG(quantity) AS mean_daily_demand,
    STDDEV_SAMP(quantity) AS std_daily_demand,
    CASE WHEN AVG(quantity) > 0
         THEN STDDEV_SAMP(quantity) / AVG(quantity) ELSE NULL END AS cv_demand,
    SUM(quantity) AS total_quantity_90d
FROM dense
GROUP BY 1;
