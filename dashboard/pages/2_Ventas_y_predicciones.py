"""
Ventas y predicciones: grid de categorías tipo tienda, gráficos actual vs predicho (Plotly tema oscuro).
Carga: data/predictions/forecasting_predictions.parquet o .csv
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
from paths import PREDICTIONS_PARQUET, PREDICTIONS_CSV
from theme import inject_theme, ACCENT

st.set_page_config(page_title="Ventas y predicciones | Forecasting Licores", page_icon="📈", layout="wide")
check_auth()
inject_theme()


@st.cache_data(ttl=300)
def load_predictions(path_parquet: str, path_csv: str) -> pd.DataFrame | None:
    p_pq, p_csv = Path(path_parquet), Path(path_csv)
    if p_pq.exists():
        return pd.read_parquet(p_pq)
    if p_csv.exists():
        df = pd.read_csv(p_csv)
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"])
        return df
    return None


df = load_predictions(str(PREDICTIONS_PARQUET), str(PREDICTIONS_CSV))
if df is None or df.empty:
    st.warning(
        "No hay predicciones de ventas disponibles en este momento. "
        "El equipo de datos las actualizará tras la próxima ejecución del forecasting."
    )
    st.stop()

actual_col = "actual" if "actual" in df.columns else "ventas_reales"
pred_col = "pred_ensemble" if "pred_ensemble" in df.columns else "ventas_predichas"
if pred_col not in df.columns and "predicho" in df.columns:
    pred_col = "predicho"
if actual_col not in df.columns:
    actual_col = df.columns[0]
if pred_col not in df.columns:
    for c in ("pred_ensemble", "predicho", "ventas_predichas"):
        if c in df.columns:
            pred_col = c
            break

# Lista de categorías para los tiles (máximo 6 para el grid 2x3)
cats_raw = sorted(df["categoria"].dropna().astype(str).unique().tolist()) if "categoria" in df.columns else []
CAT_TILE_COLORS = ["#e67e22", "#c2410c", "#b45309", "#a16207", "#92400e", "#78350f"]
category_tiles = cats_raw[:6]  # primeras 6

# Session state para categoría elegida desde tile
if "ventas_cat_sel" not in st.session_state:
    st.session_state["ventas_cat_sel"] = "Todas"

st.title("Ventas y predicciones")
st.caption(f"{len(df):,} filas | Elige una categoría para filtrar o usa el menú lateral")

# ----- Grid de categorías tipo tienda (como imagen) -----
st.markdown("#### Ver predicciones por categoría")
row1 = st.columns(3)
row2 = st.columns(3)
for i, cat in enumerate(category_tiles):
    col = row1[i % 3] if i < 3 else row2[i % 3]
    with col:
        color = CAT_TILE_COLORS[i % len(CAT_TILE_COLORS)]
        short = cat[:22] + "…" if len(cat) > 22 else cat
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(22,33,62,0.95) 100%);
                border: 1px solid {color};
                border-radius: 12px;
                padding: 1.25rem;
                text-align: center;
                margin-bottom: 0.5rem;
            ">
                <div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: #fff;">{short}</div>
                <div style="font-size: 0.8rem; color: {color}; margin-top: 0.35rem;">Ver predicciones</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ver", key=f"tile_{i}", type="primary"):
            st.session_state["ventas_cat_sel"] = cat
            st.rerun()

st.divider()

# Filtros en sidebar (por defecto la categoría del tile si se eligió)
with st.sidebar:
    st.subheader("Filtros")
    categorias = ["Todas"] + cats_raw
    cat_sel = st.selectbox(
        "Categoría",
        categorias,
        index=categorias.index(st.session_state["ventas_cat_sel"]) if st.session_state["ventas_cat_sel"] in categorias else 0,
    )
    if cat_sel != st.session_state["ventas_cat_sel"]:
        st.session_state["ventas_cat_sel"] = cat_sel
    rango = None
    if "fecha" in df.columns:
        min_f = df["fecha"].min()
        max_f = df["fecha"].max()
        rango = st.date_input("Rango fechas", value=(min_f, max_f), min_value=min_f, max_value=max_f)

mask = pd.Series(True, index=df.index)
if "categoria" in df.columns and cat_sel != "Todas":
    mask &= df["categoria"].astype(str) == cat_sel
if "fecha" in df.columns and rango is not None and len(rango) == 2:
    mask &= (df["fecha"].dt.date >= rango[0]) & (df["fecha"].dt.date <= rango[1])
df_f = df.loc[mask]

# Tema Plotly oscuro (tienda de licores)
PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="rgba(22, 33, 62, 0.9)",
        plot_bgcolor="rgba(22, 33, 62, 0.5)",
        font=dict(color="#f5f5f5", size=12),
        xaxis=dict(gridcolor="rgba(245,245,245,0.1)", zerolinecolor="rgba(245,245,245,0.2)"),
        yaxis=dict(gridcolor="rgba(245,245,245,0.1)", zerolinecolor="rgba(245,245,245,0.2)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
)


@st.fragment(run_every=None)
def _tab_serie_temporal():
    if "fecha" not in df_f.columns or len(df_f) == 0:
        st.info("No hay columna de fecha para graficar.")
        return
    agg = df_f.groupby("fecha").agg({actual_col: "sum", pred_col: "sum"}).reset_index()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=agg["fecha"], y=agg[actual_col], name="Actual",
            line=dict(color="#94a3b8", width=2), fill="tozeroy", fillcolor="rgba(148,163,184,0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=agg["fecha"], y=agg[pred_col], name="Predicho",
            line=dict(color=ACCENT, width=2.5), fill="tozeroy", fillcolor="rgba(230,126,34,0.2)",
        )
    )
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title="Actual vs predicho (serie temporal)",
        height=400,
        margin=dict(t=50, b=50, l=50, r=30),
    )
    st.plotly_chart(fig, use_container_width=True)


@st.fragment(run_every=None)
def _tab_por_categoria():
    if "categoria" not in df_f.columns or len(df_f) == 0:
        st.info("No hay columna de categoría para agrupar.")
        return
    por_cat = df_f.groupby("categoria").agg({actual_col: "sum", pred_col: "sum"}).reset_index()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=por_cat["categoria"], y=por_cat[actual_col], name="Actual", marker_color="#94a3b8")
    )
    fig.add_trace(
        go.Bar(x=por_cat["categoria"], y=por_cat[pred_col], name="Predicho", marker_color=ACCENT)
    )
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title="Actual vs predicho por categoría",
        barmode="group",
        height=400,
        margin=dict(t=50, b=80, l=50, r=30),
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)


@st.fragment(run_every=None)
def _tab_tabla_descarga():
    st.dataframe(df_f, use_container_width=True)
    csv = df_f.to_csv(index=False)
    st.download_button("Descargar CSV", data=csv, file_name="forecasting_predictions_filtered.csv", mime="text/csv")

tab_ts, tab_cat, tab_tab = st.tabs(["Actual vs predicho (serie temporal)", "Por categoría", "Tabla y descarga"])
with tab_ts:
    _tab_serie_temporal()
with tab_cat:
    _tab_por_categoria()
with tab_tab:
    _tab_tabla_descarga()
