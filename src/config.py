"""Configuration for the AI Demand Forecasting & Inventory Optimization pipeline."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUTS = PROJECT_ROOT / "outputs"
DUCKDB_PATH = DATA_PROCESSED / "retail.duckdb"

# Data source: UCI Online Retail II (CC BY 4.0), Chen (2012).
# Direct UCI download is the first choice; the Packt GitHub mirror hosts the
# same CSV (Year 2009-2010 sheet, 525,461 rows) and is the fallback used here.
UCI_XLSX_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.xlsx"
UCI_XLSX_URL_LEGACY = "https://archive.ics.uci.edu/ml/machine-learning-databases/00502/online_retail_II.xlsx"
CSV_MIRROR_URL = (
    "https://raw.githubusercontent.com/PacktWorkshops/The-Data-Analysis-Workshop"
    "/master/Chapter08/Datasets/online_retail_II.csv"
)
RAW_CSV = DATA_RAW / "online_retail_II.csv"
RAW_XLSX = DATA_RAW / "online_retail_II.xlsx"

# Forecasting
TEST_DAYS = 28            # hold-out window for model comparison
FORECAST_HORIZON_DAYS = 14  # forward forecast used for inventory planning

# Inventory planning (documented assumptions — the UCI data has no lead-time
# or on-hand-stock columns, so these are explicit, configurable parameters)
SERVICE_LEVEL_Z = 1.65    # ~95% cycle service level
DEFAULT_LEAD_TIME_DAYS = 7
LEAD_TIME_WHATIF_DAYS = [1, 3, 5, 7, 10, 14, 21]
STATS_WINDOW_DAYS = 90    # window for per-SKU demand mean / std
MIN_SKU_HISTORY_DAYS = 30  # a SKU needs this many active days to be scored

# MLflow (local file tracking)
MLFLOW_EXPERIMENT = "ai-demand-forecasting-inventory"

RANDOM_STATE = 42
