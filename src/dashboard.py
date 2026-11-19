"""Interactive Plotly dashboard (HTML export).

Three views, matching the Power BI dashboard spec in powerbi/:
  1. Forecast accuracy — actual vs Naive / ARIMA / XGBoost on the hold-out,
     plus a metrics table.
  2. Stockout risk — top risky SKUs and a CV-vs-forecast scatter.
  3. Lead-time what-if — a slider over lead-time days that recomputes the
     high-risk SKU count and total safety stock (precomputed in
     outputs/lead_time_whatif.csv).

Usage:
    python -m src.dashboard
"""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import OUTPUTS  # noqa: E402


def build_dashboard() -> Path:
    comparison = json.loads((OUTPUTS / "model_comparison.json").read_text())
    preds = pd.read_csv(OUTPUTS / "test_predictions.csv", parse_dates=["sale_date"])
    forecast = pd.read_csv(OUTPUTS / "forecast_14d.csv", parse_dates=["forecast_date"])
    plan = pd.read_csv(OUTPUTS / "inventory_plan.csv")
    whatif = pd.read_csv(OUTPUTS / "lead_time_whatif.csv")
    inventory = json.loads((OUTPUTS / "inventory_summary.json").read_text())

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "1 — Forecast accuracy: actual vs models (28-day hold-out)",
            "Model comparison (MAPE / RMSE)",
            "2 — Stockout risk: top 15 SKUs by forecast lead-time demand",
            "Demand volatility (CV) vs forecast demand",
            "3 — Lead-time what-if: high-risk SKUs vs lead time",
            "Lead-time what-if: total safety stock vs lead time",
        ),
        specs=[[{"type": "xy"}, {"type": "table"}],
               [{"type": "xy"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "xy"}]],
        vertical_spacing=0.10, horizontal_spacing=0.08,
    )

    # --- Panel 1: hold-out lines -------------------------------------------
    fig.add_trace(go.Scatter(x=preds["sale_date"], y=preds["actual"], name="Actual",
                             mode="lines+markers", line=dict(width=2)), row=1, col=1)
    for col, name in [("naive", "Naive (lag-7)"), ("arima", "ARIMA"),
                      ("xgboost", "XGBoost")]:
        fig.add_trace(go.Scatter(x=preds["sale_date"], y=preds[col], name=name,
                                 mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=forecast["forecast_date"], y=forecast["forecast_quantity"],
                             name=f"Forward forecast ({comparison['best_model']})",
                             mode="lines", line=dict(dash="dash")), row=1, col=1)

    # --- Panel 2: metrics table --------------------------------------------
    rows = [[m, f"{v['mape']:.2f}%", f"{v['rmse']:,.1f}",
             f"{v['mape_improvement_vs_naive_pct']:+.1f}%"]
            for m, v in comparison["models"].items()]
    fig.add_trace(go.Table(
        header=dict(values=["Model", "MAPE", "RMSE", "MAPE vs naive"]),
        cells=dict(values=list(zip(*rows)))), row=1, col=2)

    # --- Panel 3: top risky SKUs -------------------------------------------
    top = plan.head(15)
    colors = ["crimson" if r else "steelblue"
              for r in top["high_stockout_risk"]]
    fig.add_trace(go.Bar(x=top["forecast_lt_demand"], y=top["description"],
                         orientation="h", marker_color=colors,
                         name="Forecast LT demand",
                         hovertext=[f"ROP {rop:,.0f} · SS {ss:,.0f}"
                                    for rop, ss in zip(top["reorder_point"],
                                                       top["safety_stock"])]),
                  row=2, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)

    # --- Panel 4: CV vs forecast scatter ------------------------------------
    fig.add_trace(go.Scatter(
        x=plan["cv_demand"], y=plan["forecast_lt_demand"], mode="markers",
        marker=dict(size=6, color=plan["high_stockout_risk"].astype(int),
                    colorscale=[[0, "steelblue"], [1, "crimson"]],
                    showscale=False),
        text=plan["description"], name="SKUs (red = high risk)"), row=2, col=2)

    # --- Panels 5-6: lead-time what-if curves (one point per evaluated
    # lead time; the full what-if table is in outputs/lead_time_whatif.csv) ---
    fig.add_trace(go.Scatter(x=whatif["lead_time_days"], y=whatif["high_risk_skus"],
                             mode="lines+markers", name="High-risk SKUs",
                             line=dict(width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=whatif["lead_time_days"],
                             y=whatif["total_safety_stock_units"],
                             mode="lines+markers", name="Total safety stock (units)",
                             line=dict(width=2)), row=3, col=2)

    fig.update_layout(
        title=("AI Demand Forecasting & Inventory Optimization — "
               f"best model: {comparison['best_model'].upper()} · "
               f"high stockout-risk SKUs: {inventory['high_stockout_risk_skus']:,} "
               f"of {inventory['skus_scored']:,} scored"),
        height=1250, showlegend=True, template="plotly_white",
        margin=dict(l=60, r=40, t=90, b=60),
    )
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_yaxes(title_text="Units / day", row=1, col=1)
    fig.update_xaxes(title_text="Forecast demand over lead time (units)", row=2, col=1)
    fig.update_xaxes(title_text="CV of daily demand", row=2, col=2)
    fig.update_yaxes(title_text="Forecast demand over lead time (units)", row=2, col=2)
    fig.update_xaxes(title_text="Lead time (days)", row=3, col=1)
    fig.update_yaxes(title_text="High-risk SKUs", row=3, col=1)
    fig.update_xaxes(title_text="Lead time (days)", row=3, col=2)
    fig.update_yaxes(title_text="Safety stock (units)", row=3, col=2)

    out = OUTPUTS / "dashboard.html"
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    print(f"Dashboard written to {out}")
    return out


def main() -> int:
    build_dashboard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
