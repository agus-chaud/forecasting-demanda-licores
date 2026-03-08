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
PREDICTIONS_PARQUET = BASE / "data" / "predictions" / "forecasting_predictions.parquet"
PREDICTIONS_CSV = BASE / "data" / "predictions" / "forecasting_predictions.csv"
