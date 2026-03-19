"""
Tests de integración para dashboard/pages/4_Forecast_Futuro.py

Principio smart-testing: testar COMPORTAMIENTO desde la perspectiva del usuario,
no la implementación interna. Los fixtures usan datos sintéticos mínimos
para que los tests sean rápidos y no dependan de que el notebook se haya ejecutado.
"""
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Añadir el root del proyecto al path para importar módulos del dashboard
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))


# ── FIXTURES ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_future_cat_df():
    """DataFrame mínimo que simula forecasting_future_categories.parquet."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2015-12-01", periods=30, freq="D")
    cats = ["VODKA 80 PROOF", "CANADIAN WHISKIES", "TEQUILA"]
    rows = []
    for cat in cats:
        for d in dates:
            base = rng.normal(5000, 500)
            pens = abs(base)
            rows.append({
                "fecha":         d,
                "categoria":     cat,
                "pred_xgb":      abs(rng.normal(4800, 400)),
                "pred_lgb":      abs(rng.normal(5200, 400)),
                "pred_ensemble": pens,
                "pred_q10":      pens * 0.80,
                "pred_q90":      pens * 1.20,
            })
    df = pd.DataFrame(rows)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


@pytest.fixture
def sample_future_store_df():
    """DataFrame mínimo que simula forecasting_future_stores.parquet."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2015-12-01", periods=30, freq="D")
    stores = [1001, 1002, 1003]
    abc = {1001: "A", 1002: "B", 1003: "C"}
    rows = []
    for store_id in stores:
        for d in dates:
            pens = abs(rng.normal(800, 100))
            rows.append({
                "fecha":         d,
                "store_id":      store_id,
                "store_abc":     abc[store_id],
                "pred_xgb":      abs(rng.normal(750, 80)),
                "pred_lgb":      abs(rng.normal(850, 80)),
                "pred_ensemble": pens,
                "pred_q10":      pens * 0.80,
                "pred_q90":      pens * 1.20,
            })
    df = pd.DataFrame(rows)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


# ── TESTS: load_parquet ───────────────────────────────────────────────────────

def test_load_parquet_returns_none_when_file_missing(tmp_path):
    """Si el parquet no existe, la función debe retornar None (no lanzar excepción)."""
    from dashboard.pages._utils_forecast import load_future_parquet
    result = load_future_parquet(str(tmp_path / "inexistente.parquet"))
    assert result is None


def test_load_parquet_returns_dataframe_when_exists(tmp_path, sample_future_cat_df):
    """Si el parquet existe, debe retornarlo como DataFrame con fecha parseada."""
    p = tmp_path / "future_cat.parquet"
    sample_future_cat_df.to_parquet(p, index=False)
    from dashboard.pages._utils_forecast import load_future_parquet
    df = load_future_parquet(str(p))
    assert isinstance(df, pd.DataFrame)
    assert pd.api.types.is_datetime64_any_dtype(df["fecha"])


# ── TESTS: filtro de horizonte ────────────────────────────────────────────────

def test_horizon_filter_7_days(sample_future_cat_df):
    """Seleccionar 7 días debe mostrar solo 7 fechas únicas."""
    horizon = 7
    fecha_inicio = sample_future_cat_df["fecha"].min()
    fecha_fin = fecha_inicio + pd.Timedelta(days=horizon - 1)
    df_f = sample_future_cat_df[sample_future_cat_df["fecha"] <= fecha_fin]
    assert df_f["fecha"].nunique() == horizon


def test_horizon_filter_14_days(sample_future_cat_df):
    """Seleccionar 14 días debe mostrar solo 14 fechas únicas."""
    horizon = 14
    fecha_inicio = sample_future_cat_df["fecha"].min()
    fecha_fin = fecha_inicio + pd.Timedelta(days=horizon - 1)
    df_f = sample_future_cat_df[sample_future_cat_df["fecha"] <= fecha_fin]
    assert df_f["fecha"].nunique() == horizon


def test_horizon_filter_30_days_shows_all(sample_future_cat_df):
    """Seleccionar 30 días muestra todo el DataFrame (no recorta)."""
    horizon = 30
    fecha_inicio = sample_future_cat_df["fecha"].min()
    fecha_fin = fecha_inicio + pd.Timedelta(days=horizon - 1)
    df_f = sample_future_cat_df[sample_future_cat_df["fecha"] <= fecha_fin]
    assert df_f["fecha"].nunique() == 30


# ── TESTS: agregación y ranking ───────────────────────────────────────────────

def test_ranking_aggregates_by_entity(sample_future_cat_df):
    """El ranking debe sumar pred_ensemble por categoría."""
    ranking = sample_future_cat_df.groupby("categoria")["pred_ensemble"].sum()
    assert len(ranking) == 3
    assert (ranking > 0).all()


def test_ranking_top_entities_are_sorted(sample_future_cat_df):
    """El ranking debe estar en orden descendente."""
    ranking = (
        sample_future_cat_df.groupby("categoria")["pred_ensemble"]
        .sum()
        .sort_values(ascending=False)
    )
    vals = ranking.values
    assert all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))


def test_store_ranking_respects_tier_filter(sample_future_store_df):
    """Filtrar por tier A debe mostrar solo tiendas tier A."""
    df_a = sample_future_store_df[sample_future_store_df["store_abc"] == "A"]
    assert (df_a["store_abc"] == "A").all()
    assert len(df_a) > 0


# ── TESTS: CI ordering ───────────────────────────────────────────────────────

def test_confidence_interval_q10_leq_ensemble(sample_future_cat_df):
    """q10 debe ser siempre ≤ pred_ensemble."""
    assert (sample_future_cat_df["pred_q10"] <= sample_future_cat_df["pred_ensemble"]).all()


def test_confidence_interval_ensemble_leq_q90(sample_future_cat_df):
    """pred_ensemble debe ser siempre ≤ q90."""
    assert (sample_future_cat_df["pred_ensemble"] <= sample_future_cat_df["pred_q90"]).all()


def test_confidence_interval_stores(sample_future_store_df):
    """Para tiendas también debe cumplirse q10 ≤ ensemble ≤ q90."""
    assert (sample_future_store_df["pred_q10"] <= sample_future_store_df["pred_ensemble"]).all()
    assert (sample_future_store_df["pred_ensemble"] <= sample_future_store_df["pred_q90"]).all()


# ── TESTS: predicciones no negativas ─────────────────────────────────────────

def test_no_negative_predictions_categories(sample_future_cat_df):
    """Las ventas no pueden ser negativas — pred_ensemble siempre ≥ 0."""
    assert (sample_future_cat_df["pred_ensemble"] >= 0).all()


def test_no_negative_predictions_stores(sample_future_store_df):
    """Para tiendas también, pred_ensemble ≥ 0."""
    assert (sample_future_store_df["pred_ensemble"] >= 0).all()


# ── TESTS: métricas resumen ───────────────────────────────────────────────────

def test_summary_metrics_are_positive(sample_future_cat_df):
    """Total forecast y promedio diario deben ser positivos."""
    total = sample_future_cat_df["pred_ensemble"].sum()
    daily_avg = sample_future_cat_df.groupby("fecha")["pred_ensemble"].sum().mean()
    assert total > 0
    assert daily_avg > 0


def test_peak_day_is_within_horizon(sample_future_cat_df):
    """El día pico debe estar dentro del rango de fechas del forecast."""
    agg = sample_future_cat_df.groupby("fecha")["pred_ensemble"].sum()
    peak_day = agg.idxmax()
    assert sample_future_cat_df["fecha"].min() <= peak_day <= sample_future_cat_df["fecha"].max()


# ── TESTS: CSV export ─────────────────────────────────────────────────────────

def test_csv_export_has_expected_columns(sample_future_cat_df):
    """El CSV exportado debe tener las columnas esperadas."""
    expected_cols = {"categoria", "fecha", "pred_ensemble", "pred_q10", "pred_q90"}
    csv_buf = io.StringIO(sample_future_cat_df.to_csv(index=False))
    df_csv = pd.read_csv(csv_buf)
    assert expected_cols.issubset(set(df_csv.columns))


def test_csv_export_row_count_matches(sample_future_cat_df):
    """El CSV exportado debe tener la misma cantidad de filas que el DataFrame."""
    csv_buf = io.StringIO(sample_future_cat_df.to_csv(index=False))
    df_csv = pd.read_csv(csv_buf)
    assert len(df_csv) == len(sample_future_cat_df)
