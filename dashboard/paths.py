"""Rutas base para datos del dashboard. CWD = directorio desde donde se ejecuta streamlit (recomendado: raíz del repo)."""
from pathlib import Path

# Si corremos desde repo: streamlit run dashboard/app.py → cwd = repo root
# Si corremos desde dashboard: streamlit run app.py → cwd = dashboard
_ROOT = Path.cwd()
if (_ROOT / "artifacts" / "modeling").exists():
    BASE = _ROOT
else:
    BASE = _ROOT.parent

MANIFEST_PATH = BASE / "artifacts" / "modeling" / "experiment_manifest_latest.json"
HISTORY_PATH = BASE / "artifacts" / "modeling" / "experiments_history.csv"

# Predicciones agregadas por categoría de producto (vista principal del dashboard)
PREDICTIONS_PARQUET = BASE / "data" / "predictions" / "forecasting_predictions.parquet"
PREDICTIONS_CSV = BASE / "data" / "predictions" / "forecasting_predictions.csv"

# Predicciones por tienda (para vista secundaria agrupada por tier/store_abc)
PREDICTIONS_BY_STORE_PARQUET = BASE / "data" / "predictions" / "forecasting_predictions_by_store.parquet"

# Forecast futuro (horizonte) para categorías y tiendas
FUTURE_CATEGORIES_PARQUET = BASE / "data" / "predictions" / "forecasting_future_categories.parquet"
FUTURE_STORES_PARQUET = BASE / "data" / "predictions" / "forecasting_future_stores.parquet"
