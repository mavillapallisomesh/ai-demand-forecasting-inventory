"""Model training & comparison: Naive baseline vs ARIMA vs XGBoost.

- Naive baseline: seasonal naive — forecast = same weekday last week (lag 7).
- ARIMA: statsmodels ARIMA, order chosen by AIC over a small grid on the
  training window only (kept small so a full run takes minutes, not hours).
- XGBoost: gradient-boosted trees on lag / rolling / calendar features.
Metrics: MAPE and RMSE on the last TEST_DAYS of the series (out-of-sample).
Every model is logged to MLflow (local file tracking) with parameters,
metrics and the fitted model artifact.

Usage:
    python -m src.train [--no-mlflow]
"""
import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import (  # noqa: E402
    FORECAST_HORIZON_DAYS, MLFLOW_EXPERIMENT, OUTPUTS, PROJECT_ROOT,
    RANDOM_STATE, TEST_DAYS,
)
from features import FEATURE_COLUMNS, load_daily_series, make_features  # noqa: E402

warnings.filterwarnings("ignore")


def mape(y_true, y_pred) -> float:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true, dtype=float)
                                  - np.asarray(y_pred, dtype=float)) ** 2)))


def naive_seasonal_forecast(train: pd.Series, horizon: int) -> np.ndarray:
    """Repeat the last 7 observed values (same weekday last week)."""
    last_week = train.iloc[-7:].values
    return np.array([last_week[i % 7] for i in range(horizon)])


def fit_arima(train: pd.Series, horizon: int):
    """Small AIC grid search; returns (forecast, order, aic)."""
    from statsmodels.tsa.arima.model import ARIMA

    best = None
    for order in [(1, 1, 1), (2, 1, 1), (1, 1, 0), (0, 1, 1), (2, 1, 2), (1, 1, 2), (0, 1, 2)]:
        try:
            res = ARIMA(train, order=order).fit()
            if best is None or res.aic < best[2]:
                best = (res, order, res.aic)
        except Exception:  # noqa: BLE001 - some orders fail to converge; skip
            continue
    if best is None:
        raise RuntimeError("All ARIMA orders failed to fit.")
    res, order, aic = best
    forecast = res.forecast(steps=horizon)
    return np.asarray(forecast, dtype=float), order, float(aic)


def fit_xgboost(feat: pd.DataFrame, test_days: int, horizon: int):
    """Train on all but the last `test_days`; forecast the test window, then
    refit on the full series and forecast `horizon` days ahead.
    The target is log1p(units): daily demand is right-skewed, and the log
    target materially improves MAPE on this series. Predictions are mapped
    back with expm1 before scoring or feeding back as lags."""
    import xgboost as xgb

    data = feat.dropna(subset=FEATURE_COLUMNS + ["total_quantity"]).copy()
    train_df = data.iloc[:-test_days]
    test_df = data.iloc[-test_days:]
    params = {
        "objective": "reg:squarederror",
        "max_depth": 5,
        "learning_rate": 0.05,
        "n_estimators": 400,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "random_state": RANDOM_STATE,
        "n_jobs": 4,
    }
    model = xgb.XGBRegressor(**params)
    model.fit(train_df[FEATURE_COLUMNS], np.log1p(train_df["total_quantity"]))
    test_pred = np.expm1(model.predict(test_df[FEATURE_COLUMNS]))

    # Refit on the full history for the forward forecast.
    full = xgb.XGBRegressor(**params)
    full.fit(data[FEATURE_COLUMNS], np.log1p(data["total_quantity"]))
    # Recursive multi-step forecast: feed predictions back as lags.
    hist = data["total_quantity"].copy()
    future_idx = pd.date_range(data.index[-1] + pd.Timedelta(days=1),
                               periods=horizon, freq="D")
    future_preds: list[float] = []
    for i, day in enumerate(future_idx):
        extended = pd.concat(
            [hist, pd.Series(future_preds, index=future_idx[:i])])
        next_xmas = pd.Timestamp(
            f"{day.year if day.month < 12 or day.day <= 25 else day.year + 1}-12-25")
        row = {
            "dow": day.dayofweek, "month": day.month,
            "is_weekend": int(day.dayofweek >= 5),
            "dow_sin": float(np.sin(2 * np.pi * day.dayofweek / 7)),
            "dow_cos": float(np.cos(2 * np.pi * day.dayofweek / 7)),
            "trend": len(data) + i,
            "days_to_christmas": int(np.clip((next_xmas - day).days, 0, 60)),
            "lag_1": extended.iloc[-1],
            "lag_2": extended.iloc[-2],
            "lag_3": extended.iloc[-3],
            "lag_7": extended.iloc[-7],
            "lag_14": extended.iloc[-14],
            "lag_21": extended.iloc[-21],
            "lag_28": extended.iloc[-28],
            "roll_mean_7": extended.iloc[-7:].mean(),
            "roll_std_7": extended.iloc[-7:].std(),
            "roll_mean_14": extended.iloc[-14:].mean(),
            "roll_mean_28": extended.iloc[-28:].mean(),
            "roll_std_28": extended.iloc[-28:].std(),
        }
        pred = float(np.expm1(full.predict(pd.DataFrame([row])[FEATURE_COLUMNS])[0]))
        future_preds.append(pred)
    future = np.array(future_preds)
    return test_pred, future, model, full, test_df.index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-mlflow", action="store_true", help="skip MLflow logging")
    args = parser.parse_args()

    daily = load_daily_series()
    daily["total_quantity"] = daily["total_quantity"].interpolate(limit_direction="both")
    y = daily["total_quantity"]
    train, test = y.iloc[:-TEST_DAYS], y.iloc[-TEST_DAYS:]
    print(f"series: {len(y)} days ({y.index[0].date()} .. {y.index[-1].date()}); "
          f"train={len(train)}, test={len(test)}")

    results = {}

    # 1) Naive seasonal baseline
    naive_pred = naive_seasonal_forecast(train, TEST_DAYS)
    results["naive"] = {"mape": mape(test, naive_pred), "rmse": rmse(test, naive_pred)}

    # 2) ARIMA
    arima_pred, arima_order, arima_aic = fit_arima(train, TEST_DAYS)
    results["arima"] = {"mape": mape(test, arima_pred), "rmse": rmse(test, arima_pred),
                        "order": list(arima_order), "aic": arima_aic}

    # 3) XGBoost
    feat = make_features(daily)
    xgb_test_pred, xgb_future, xgb_model, xgb_full_model, test_idx = fit_xgboost(
        feat, TEST_DAYS, FORECAST_HORIZON_DAYS)
    results["xgboost"] = {"mape": mape(test, xgb_test_pred),
                          "rmse": rmse(test, xgb_test_pred)}

    best_name = min(results, key=lambda k: results[k]["mape"])
    for name, m in results.items():
        improvement = (results["naive"]["mape"] - m["mape"]) / results["naive"]["mape"] * 100
        m["mape_improvement_vs_naive_pct"] = improvement
        print(f"{name:<8} MAPE={m['mape']:6.2f}%  RMSE={m['rmse']:9.1f}  "
              f"vs naive: {improvement:+.1f}%")
    print(f"Best model (lowest MAPE): {best_name}")

    # Forward forecasts from the best model (refit on full history).
    if best_name == "xgboost":
        future_forecast = xgb_future
    elif best_name == "arima":
        future_forecast, _, _ = fit_arima(y, FORECAST_HORIZON_DAYS)
    else:
        future_forecast = naive_seasonal_forecast(y, FORECAST_HORIZON_DAYS)
    future_idx = pd.date_range(y.index[-1] + pd.Timedelta(days=1),
                               periods=FORECAST_HORIZON_DAYS, freq="D")
    forecast_df = pd.DataFrame({"forecast_date": future_idx,
                                "forecast_quantity": np.maximum(future_forecast, 0),
                                "model": best_name})
    test_frame = pd.DataFrame({
        "sale_date": test.index,
        "actual": test.values,
        "naive": naive_pred,
        "arima": arima_pred,
        "xgboost": xgb_test_pred,
    })

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    test_frame.to_csv(OUTPUTS / "test_predictions.csv", index=False)
    forecast_df.to_csv(OUTPUTS / "forecast_14d.csv", index=False)
    payload = {"best_model": best_name, "test_days": TEST_DAYS,
               "horizon_days": FORECAST_HORIZON_DAYS, "models": results}
    (OUTPUTS / "model_comparison.json").write_text(json.dumps(payload, indent=2))

    if not args.no_mlflow:
        import os

        # MLflow >= 3 refuses the local file store unless opted in.
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        import mlflow

        mlflow.set_tracking_uri(f"file://{PROJECT_ROOT / 'mlruns'}")
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        with mlflow.start_run(run_name="model-comparison"):
            mlflow.log_param("test_days", TEST_DAYS)
            mlflow.log_param("horizon_days", FORECAST_HORIZON_DAYS)
            mlflow.log_param("arima_order", str(arima_order))
            mlflow.log_param("best_model", best_name)
            for name, m in results.items():
                mlflow.log_metric(f"{name}_mape", m["mape"])
                mlflow.log_metric(f"{name}_rmse", m["rmse"])
            mlflow.log_artifact(str(OUTPUTS / "test_predictions.csv"))
            mlflow.log_artifact(str(OUTPUTS / "forecast_14d.csv"))
            # The fitted XGBoost model (refit on the full history) is saved in
            # XGBoost's native format and logged as a plain artifact. The
            # Booster (not the sklearn wrapper) is saved: XGBRegressor's
            # save_model() breaks on scikit-learn >= 1.7, which removed the
            # `_estimator_type` attribute xgboost 2.1.4 still reads.
            # Load it back with: xgboost.Booster(model_file="xgboost_model.json")
            model_path = OUTPUTS / "xgboost_model.json"
            xgb_full_model.get_booster().save_model(str(model_path))
            mlflow.log_artifact(str(model_path))
        print(f"MLflow run logged to {PROJECT_ROOT / 'mlruns'}")

    print("Wrote outputs/test_predictions.csv, outputs/forecast_14d.csv, "
          "outputs/model_comparison.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
