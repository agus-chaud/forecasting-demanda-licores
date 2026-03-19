"""
Forecast Futuro — predicciones más allá de los datos históricos disponibles.
Generadas por Fase 9 del notebook usando recursive multi-step forecasting.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
from pages._utils_forecast import load_future_parquet
from paths import (
    FUTURE_PREDICTIONS_CAT_PARQUET,
    FUTURE_PREDICTIONS_STORE_PARQUET,
    PREDICTIONS_PARQUET,
    PREDICTIONS_BY_STORE_PARQUET,
)
from theme import ACCENT, inject_theme

st.set_page_config(
    page_title="Forecast Futuro | Forecasting Licores",
    page_icon="📈",
    layout="wide",
)
check_auth()
inject_theme()

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F8F8F8", size=12, family="Inter"),
        xaxis=dict(gridcolor="#27272A", zerolinecolor="#27272A"),
        yaxis=dict(gridcolor="#27272A", zerolinecolor="#27272A"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
)


@st.cache_data(ttl=300)
def load_parquet(path: str) -> pd.DataFrame | None:
    return load_future_parquet(path)


# ── Cargar datos ──────────────────────────────────────────────────────────────
df_future_cat   = load_parquet(str(FUTURE_PREDICTIONS_CAT_PARQUET))
df_future_store = load_parquet(str(FUTURE_PREDICTIONS_STORE_PARQUET))
df_test_cat     = load_parquet(str(PREDICTIONS_PARQUET))
df_test_store   = load_parquet(str(PREDICTIONS_BY_STORE_PARQUET))

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Configuración")

    entity_type = st.radio("Vista", ["Categorías", "Tiendas"], horizontal=True)

    horizon = st.selectbox("Horizonte de forecast", [7, 14, 30], index=2, format_func=lambda x: f"{x} días")

    if entity_type == "Categorías":
        cats = ["Todas"]
        if df_future_cat is not None:
            cats += sorted(df_future_cat["categoria"].dropna().unique().tolist())
        entity_sel = st.selectbox("Categoría", cats)
    else:
        tier_filter = st.selectbox("Tier ABC", ["Todos", "A", "B", "C"])
        stores = []
        if df_future_store is not None:
            _s = df_future_store.copy()
            if tier_filter != "Todos":
                _s = _s[_s["store_abc"] == tier_filter]
            stores = ["Todas"] + sorted(_s["store_id"].astype(str).unique().tolist())
        entity_sel = st.selectbox("Tienda", stores)

    show_ci = st.checkbox("Mostrar intervalo de confianza (q10-q90)", value=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("Forecast Futuro")
st.caption(
    "Predicciones para días aún no transcurridos. "
    "Generadas con recursive multi-step forecasting (XGBoost + LightGBM ensemble)."
)

# ── Verificar datos disponibles ───────────────────────────────────────────────
if entity_type == "Categorías":
    df_future = df_future_cat
    df_test   = df_test_cat
    entity_col = "categoria"
    actual_col = "actual"
else:
    df_future = df_future_store
    df_test   = df_test_store
    entity_col = "store_id"
    actual_col = "actual"

if df_future is None or df_future.empty:
    st.warning(
        "No se encontró el archivo de forecast futuro. "
        "Ejecutá la **Fase 9** del notebook `forecasting-licores.ipynb` para generarlo."
    )
    st.stop()

# ── Filtrar por horizonte y entidad ──────────────────────────────────────────
fecha_inicio = df_future["fecha"].min()
fecha_fin    = fecha_inicio + pd.Timedelta(days=horizon - 1)
df_fut_f = df_future[df_future["fecha"] <= fecha_fin].copy()

if entity_sel not in ["Todas", "Todas"]:
    df_fut_f = df_fut_f[df_fut_f[entity_col].astype(str) == entity_sel]
    if df_test is not None:
        df_test_f = df_test[df_test[entity_col].astype(str) == entity_sel]
    else:
        df_test_f = None
else:
    df_test_f = df_test

if len(df_fut_f) == 0:
    st.info("Sin datos para el filtro seleccionado.")
    st.stop()

# ── Agregar por fecha ─────────────────────────────────────────────────────────
agg_future = df_fut_f.groupby("fecha").agg(
    pred_ensemble=("pred_ensemble", "sum"),
    pred_q10=("pred_q10", "sum"),
    pred_q90=("pred_q90", "sum"),
).reset_index()

# Contexto de backtesting (período de test, muestra precisión del modelo)
agg_test = None
if df_test_f is not None and not df_test_f.empty:
    _agg_cols = {"pred_ensemble": ("pred_ensemble", "sum")}
    if actual_col in df_test_f.columns:
        _agg_cols["actual"] = (actual_col, "sum")
    agg_test = df_test_f.groupby("fecha").agg(**_agg_cols).reset_index()

# Fecha de corte (último dato real conocido)
fecha_corte = fecha_inicio - pd.Timedelta(days=1)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Línea de tiempo", "🏆 Ranking", "📋 Tabla"])

# ── TAB 1: Gráfico principal ──────────────────────────────────────────────────
with tab1:
    fig = go.Figure()

    # Zona de forecast (rectángulo sombreado)
    fig.add_vrect(
        x0=fecha_corte,
        x1=fecha_fin,
        fillcolor=ACCENT,
        opacity=0.05,
        line_width=0,
        annotation_text="Zona de forecast",
        annotation_position="top left",
        annotation_font_color=ACCENT,
    )

    # Línea vertical: "Último dato real"
    fig.add_vline(
        x=fecha_corte,
        line_dash="dash",
        line_color=ACCENT,
        line_width=1.5,
        annotation_text="Último dato real",
        annotation_position="top right",
        annotation_font_color=ACCENT,
    )

    # Traza 1: backtesting — valor real (contexto histórico)
    if agg_test is not None and "actual" in agg_test.columns:
        fig.add_trace(go.Scatter(
            x=agg_test["fecha"],
            y=agg_test["actual"],
            name="Real (test)",
            line=dict(color="#94a3b8", width=1.5),
            mode="lines",
        ))

    # Traza 2: backtesting — predicción del modelo (muestra calibración)
    if agg_test is not None and "pred_ensemble" in agg_test.columns:
        fig.add_trace(go.Scatter(
            x=agg_test["fecha"],
            y=agg_test["pred_ensemble"],
            name="Predicho (test)",
            line=dict(color=ACCENT, width=1.5, dash="dot"),
            mode="lines",
        ))

    # Traza 3+4: CI band q10/q90 (solo si está activado)
    if show_ci and "pred_q90" in agg_future.columns:
        fig.add_trace(go.Scatter(
            x=agg_future["fecha"],
            y=agg_future["pred_q90"],
            name="q90",
            line=dict(width=0),
            mode="lines",
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=agg_future["fecha"],
            y=agg_future["pred_q10"],
            name="Intervalo confianza (q10-q90)",
            fill="tonexty",
            fillcolor=f"rgba(217,160,91,0.15)",
            line=dict(width=0),
            mode="lines",
        ))

    # Traza 5: forecast futuro (línea principal)
    fig.add_trace(go.Scatter(
        x=agg_future["fecha"],
        y=agg_future["pred_ensemble"],
        name="Forecast futuro",
        line=dict(color=ACCENT, width=3),
        mode="lines+markers",
        marker=dict(size=5),
    ))

    _title = f"Forecast {'agregado' if entity_sel in ['Todas','Todas'] else entity_sel} — próximos {horizon} días"
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title=_title,
        height=420,
        xaxis_title="Fecha",
        yaxis_title="Ventas ($)",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Métricas resumen
    col1, col2, col3 = st.columns(3)
    _total = agg_future["pred_ensemble"].sum()
    _daily_avg = agg_future["pred_ensemble"].mean()
    _peak_day = agg_future.loc[agg_future["pred_ensemble"].idxmax(), "fecha"]
    col1.metric("Total forecast", f"${_total:,.0f}")
    col2.metric("Promedio diario", f"${_daily_avg:,.0f}")
    col3.metric("Día pico predicho", str(_peak_day.date()))

# ── TAB 2: Ranking ────────────────────────────────────────────────────────────
with tab2:
    _rank = (
        df_fut_f.groupby(entity_col)["pred_ensemble"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    _rank.columns = [entity_col, "Forecast total ($)"]

    fig_bar = go.Figure(go.Bar(
        x=_rank[entity_col].astype(str),
        y=_rank["Forecast total ($)"],
        marker_color=ACCENT,
        text=_rank["Forecast total ($)"].apply(lambda x: f"${x:,.0f}"),
        textposition="outside",
    ))
    fig_bar.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title=f"Top 10 {entity_type.lower()} por forecast total ({horizon} días)",
        height=420,
        xaxis_tickangle=-35,
        yaxis_title="Ventas ($)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── TAB 3: Tabla + Descarga ───────────────────────────────────────────────────
with tab3:
    _display = df_fut_f[[entity_col, "fecha", "pred_ensemble", "pred_q10", "pred_q90"]].copy()
    _display["fecha"] = _display["fecha"].dt.date
    _display["pred_ensemble"] = _display["pred_ensemble"].round(2)
    _display["pred_q10"]      = _display["pred_q10"].round(2)
    _display["pred_q90"]      = _display["pred_q90"].round(2)
    _display = _display.sort_values(["fecha", entity_col]).reset_index(drop=True)

    st.dataframe(_display, use_container_width=True, height=400)

    _csv = _display.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Descargar CSV",
        data=_csv,
        file_name=f"forecast_futuro_{entity_type.lower()}_{horizon}d.csv",
        mime="text/csv",
    )
