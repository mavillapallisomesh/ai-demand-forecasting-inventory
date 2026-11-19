# Data model

Star schema with two fact tables and one parameter (what-if) table. No
conformed dimensions are needed beyond the date/SKU keys already in the
export files.

## Tables

### `Daily Sales` (fact, grain: one row per day)
| Column | Type | Notes |
|---|---|---|
| sale_date | Date | calendar day |
| total_quantity | Whole number | actual units sold |
| total_revenue | Decimal | actual revenue |
| n_orders | Whole number | distinct invoices |
| n_skus | Whole number | distinct SKUs sold |
| forecast_quantity | Whole number | 14-day forward forecast (blank outside the forecast window) |

### `SKU Inventory` (fact, grain: one row per SKU)
| Column | Type | Notes |
|---|---|---|
| stock_code | Text | SKU key |
| description | Text | product name |
| mean_daily_demand | Decimal | 90-day mean of daily units |
| std_daily_demand | Decimal | 90-day std of daily units |
| cv_demand | Decimal | std / mean (volatility) |
| safety_stock | Decimal | z·σ·√LT, z = 1.65, LT = 7 days (default) |
| reorder_point | Decimal | mean·LT + safety stock |
| forecast_lt_demand | Decimal | forecast demand over the lead time |
| days_of_cover | Decimal | reorder_point / mean daily demand |
| high_stockout_risk | True/False | forecast LT demand > ROP, or (CV > 1 and forecast rising) |
| share_28d | Decimal | share of last-28-day demand (forecast allocation key) |

### `Lead Time What-If` (parameter table, grain: one row per lead time)
| Column | Type | Notes |
|---|---|---|
| lead_time_days | Whole number | 1, 3, 5, 7, 10, 14, 21 |
| skus_scored | Whole number | SKUs in the plan at this lead time |
| high_risk_skus | Whole number | flagged SKUs at this lead time |
| total_safety_stock_units | Decimal | sum of safety stock at this lead time |
| total_reorder_point_units | Decimal | sum of ROP at this lead time |

## Relationships

- `Daily Sales[sale_date]` — no relationship needed (single fact for page 1).
- `SKU Inventory[stock_code]` — no relationship needed (single fact for page 2).
- `Lead Time What-If[lead_time_days]` — **no active relationship**; it is a
  disconnected parameter table driving the what-if cards via DAX (`SELECTEDVALUE`).
  This is the standard Power BI what-if pattern.
