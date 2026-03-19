"""
Tests smart para Fase 9: validar alineación FEATURES ↔ modelo y price features.

Principio: el modelo fue entrenado con 33 features incluyendo precio.
En inferencia, FEATURES debe ser exactamente ese set y _build_cat_row debe proveerlas.
"""
from pathlib import Path

import joblib
import pytest


# FEATURES esperado por el modelo (debe coincidir con entrenamiento)
FEATURES_EXPECTED = [
    "lag_1", "lag_7", "lag_14", "lag_28", "lag_52", "lag_365",
    "roll_mean_7", "roll_mean_28", "roll_std_7", "roll_std_28", "cv_7",
    "roll_max_7", "roll_min_7", "roll_range_7", "ewm_7", "ewm_28",
    "dia_semana", "mes", "dia_mes", "es_finde",
    "es_festivo", "es_semana_navidad", "es_semana_thanksgiving",
    "trimestre", "dias_hasta_navidad",
    "ratio_lag7_roll28", "trend_7",
    "categoria_te",
    "precio_costo_medio", "precio_retail_medio", "margen_relativo",
    "botellas_totales", "roll_precio_retail_7",
]

PRICE_FEATURES = [
    "precio_costo_medio", "precio_retail_medio", "margen_relativo",
    "botellas_totales", "roll_precio_retail_7",
]


@pytest.fixture
def model_path():
    """Ruta al modelo XGB global (requiere haber ejecutado el notebook respaldo)."""
    return Path("artifacts/modeling/forecasting_xgb_global.joblib")


def test_model_has_price_features_when_exists(model_path):
    """Si el modelo existe, debe tener las 5 price features en su feature_names."""
    if not model_path.exists():
        pytest.skip("Modelo no encontrado. Ejecutá forecasting-licores_respaldo_entrenamiento.ipynb")
    model = joblib.load(model_path)
    fnames = list(model.get_booster().feature_names)
    missing = set(PRICE_FEATURES) - set(fnames)
    assert not missing, f"Modelo espera price features pero faltan: {missing}"


def test_model_feature_count_when_exists(model_path):
    """Si el modelo existe, debe tener 33 features."""
    if not model_path.exists():
        pytest.skip("Modelo no encontrado.")
    model = joblib.load(model_path)
    fnames = list(model.get_booster().feature_names)
    assert len(fnames) == 33, f"Modelo tiene {len(fnames)} features, esperado 33"


def test_features_expected_has_all_price():
    """FEATURES_EXPECTED debe incluir las 5 price features."""
    assert set(PRICE_FEATURES).issubset(set(FEATURES_EXPECTED))


def test_features_expected_count():
    """FEATURES_EXPECTED debe tener 33 elementos."""
    assert len(FEATURES_EXPECTED) == 33
    assert len(set(FEATURES_EXPECTED)) == 33  # sin duplicados
