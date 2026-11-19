# DAX measures

Copy-paste ready. Create them under Modeling → New measure in the table
named in brackets.

## Page 1 — Forecast accuracy

```dax
-- [Daily Sales]
Actual Units = SUM('Daily Sales'[total_quantity])

Forward Forecast Units = SUM('Daily Sales'[forecast_quantity])

-- Hold-out metrics are computed by the pipeline (see outputs/model_comparison.json)
-- and shown as cards. After each run, copy the measured MAPE/RMSE values from
-- outputs/model_comparison.json into card visuals (or import the test
-- predictions file and use the dynamic measures below — recommended).

```dax
-- [Test Predictions] (optional import of outputs/test_predictions.csv)
MAPE XGBoost (%) =
AVERAGEX(
    FILTER('Test Predictions', 'Test Predictions'[actual] <> 0),
    ABS('Test Predictions'[actual] - 'Test Predictions'[xgboost])
        / 'Test Predictions'[actual]
) * 100

RMSE XGBoost =
SQRT(
    AVERAGEX(
        'Test Predictions',
        ('Test Predictions'[actual] - 'Test Predictions'[xgboost]) ^ 2
    )
)
```

## Page 2 — Stockout risk

```dax
-- [SKU Inventory]
High-Risk SKU Count =
CALCULATE(COUNTROWS('SKU Inventory'), 'SKU Inventory'[high_stockout_risk] = TRUE())

SKUs Scored = COUNTROWS('SKU Inventory')

Total Safety Stock (units) = SUM('SKU Inventory'[safety_stock])

Total Reorder Point (units) = SUM('SKU Inventory'[reorder_point])

High-Risk Share (%) =
DIVIDE([High-Risk SKU Count], [SKUs Scored]) * 100
```

## Page 3 — Lead-time what-if

```dax
-- [Lead Time What-If] — disconnected parameter table, driven by a slicer
Selected Lead Time (days) = SELECTEDVALUE('Lead Time What-If'[lead_time_days], 7)

High-Risk SKUs (What-If) =
CALCULATE(
    SUM('Lead Time What-If'[high_risk_skus]),
    'Lead Time What-If'[lead_time_days] = [Selected Lead Time (days)]
)

Total Safety Stock (What-If) =
CALCULATE(
    SUM('Lead Time What-If'[total_safety_stock_units]),
    'Lead Time What-If'[lead_time_days] = [Selected Lead Time (days)]
)
```
