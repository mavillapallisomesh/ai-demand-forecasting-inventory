# Power BI dashboard — rebuild instructions

Power BI `.pbix` files cannot be generated from code, so this folder ships
everything needed to rebuild the same dashboard in Power BI Desktop in
~15 minutes, plus a working interactive equivalent (`outputs/dashboard.html`,
built with Plotly) that shows the exact same views.

## Files

| File | What it is |
|---|---|
| `dataset/daily_sales.csv` | Daily totals + 14-day forecast (accuracy views) |
| `dataset/sku_forecast_inventory.csv` | Per-SKU stats, safety stock, ROP, risk flag (risk views) |
| `dataset/lead_time_whatif.csv` | What-if table for the lead-time slicer |
| `data_model.md` | Star-schema / relationships |
| `dax_measures.md` | Every DAX measure used, copy-paste ready |

## Rebuild steps (Power BI Desktop)

1. **Get Data → Text/CSV** and load the three files in `dataset/`.
   Rename the queries `Daily Sales`, `SKU Inventory`, `Lead Time What-If`.
2. **Model view** — create the relationships in `data_model.md`.
3. **Create the measures** in `dax_measures.md` (Modeling → New measure).
4. **Build three pages:**
   - **Page 1 — Forecast accuracy:** line chart of `Actual Units` vs
     `Naive Forecast`, `ARIMA Forecast`, `XGBoost Forecast` by date, plus a
     card/matrix with `MAPE (Best Model)` and `RMSE (Best Model)`; add a
     second line visual for the 14-day forward forecast.
   - **Page 2 — Stockout risk:** bar chart of top 15 SKUs by
     `Forecast Demand (Lead Time)` coloured by `High Stockout Risk`;
     scatter of `CV of Daily Demand` vs `Forecast Demand (Lead Time)`;
     KPI cards: `High-Risk SKU Count`, `Total Safety Stock (units)`.
   - **Page 3 — Lead-time what-if:** slicer on `Lead Time (days)` from the
     what-if table; cards showing `High-Risk SKUs (What-If)` and
     `Total Safety Stock (What-If)`; line charts of both measures vs lead time.
5. **Publish** to the Power BI service and schedule refresh against the
   regenerated CSVs (or point the queries at the pipeline output folder).

## Data model

See `data_model.md`. Grain: one row per day (`Daily Sales`), one row per SKU
(`SKU Inventory`), one row per evaluated lead time (`Lead Time What-If`).
