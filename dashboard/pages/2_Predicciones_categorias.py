"""
Predicciones por categoría de producto.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
from paths import PREDICTIONS_CSV, PREDICTIONS_PARQUET
from theme import ACCENT, inject_theme

st.set_page_config(page_title="Predicciones por categoría | Forecasting Licores", page_icon="🛍️", layout="wide")
check_auth()
inject_theme()


@st.cache_data(ttl=300)
def load_predictions(path_parquet: str, path_csv: str | None = None) -> pd.DataFrame | None:
    p_pq = Path(path_parquet)
    p_csv = Path(path_csv) if path_csv else None
    if p_pq.exists():
        df = pd.read_parquet(p_pq)
    elif p_csv is not None and p_csv.exists():
        df = pd.read_csv(p_csv)
    else:
        return None
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def is_contaminated_category_file(df: pd.DataFrame) -> bool:
    if "categoria" not in df.columns:
        return True
    looks_store = {"store_id", "store_abc"}.issubset(df.columns)
    cat_values = df["categoria"].dropna().astype(str)
    tier_like = len(cat_values) > 0 and cat_values.str.startswith("Tienda tier").all()
    return bool(looks_store and tier_like)


def draw_tiles(values: list[str], state_key: str, prefix_key: str) -> None:
    if not values:
        st.info("No hay valores para mostrar en tarjetas.")
        return
    # Use single ACCENT color instead of multiple colors
    color = ACCENT
    row1 = st.columns(3)
    row2 = st.columns(3)
    for i, val in enumerate(values[:6]):
        col = row1[i % 3] if i < 3 else row2[i % 3]
        with col:
            short = val[:26] + "..." if len(val) > 26 else val
            st.markdown(
                f"""
                <div style="
                    background: rgba(20, 20, 20, 0.6);
                    backdrop-filter: blur(12px);
                    border: 1px solid {color};
                    border-radius: 16px;
                    padding: 1.1rem;
                    text-align: center;
                    margin-bottom: 0.5rem;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                ">
                    <div style="font-family: 'Playfair Display', serif; font-size: 1.05rem; font-weight: 700; color: #F8F8F8;">{short}</div>
                    <div style="font-family: 'Inter', sans-serif; font-size: 0.8rem; color: {color}; margin-top: 0.35rem;">Ver predicciones</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Ver", key=f"{prefix_key}_{i}", type="primary"):
                st.session_state[state_key] = val
                st.rerun()


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

df_cat = load_predictions(str(PREDICTIONS_PARQUET), str(PREDICTIONS_CSV))

st.title("Predicciones por categoría de producto")

if "ventas_cat_sel" not in st.session_state:
    st.session_state["ventas_cat_sel"] = "Todas"

# Sidebar: filtros de categorías
with st.sidebar:
    st.subheader("Filtros categorías producto")
    categorias = ["Todas"]
    cat_min = cat_max = None
    if df_cat is not None and not df_cat.empty and "categoria" in df_cat.columns:
        categorias = ["Todas"] + sorted(df_cat["categoria"].dropna().astype(str).unique().tolist())
    cat_sel = st.selectbox(
        "Categoría",
        categorias,
        index=categorias.index(st.session_state["ventas_cat_sel"]) if st.session_state["ventas_cat_sel"] in categorias else 0,
    )
    st.session_state["ventas_cat_sel"] = cat_sel
    cat_range = None
    if df_cat is not None and not df_cat.empty and "fecha" in df_cat.columns:
        cat_min = df_cat["fecha"].min()
        cat_max = df_cat["fecha"].max()
        cat_range = st.date_input("Rango fechas (categorías)", value=(cat_min, cat_max), min_value=cat_min, max_value=cat_max)

if df_cat is None or df_cat.empty:
    st.warning("No existe el archivo de predicciones por categoría de producto.")
else:
    if is_contaminated_category_file(df_cat):
        st.error(
            "El archivo de categorías está contaminado con datos de tiendas. "
            "Debes regenerar `data/predictions/forecasting_predictions.parquet` desde el bloque de categorías del notebook."
        )
    else:
        actual_col = "actual" if "actual" in df_cat.columns else "ventas"
        pred_col = "pred_ensemble" if "pred_ensemble" in df_cat.columns else "predicho"
        cats_raw = sorted(df_cat["categoria"].dropna().astype(str).unique().tolist()) if "categoria" in df_cat.columns else []
        st.caption(f"{len(df_cat):,} filas | Categorías únicas: {len(cats_raw)}")
        draw_tiles(cats_raw, "ventas_cat_sel", "tile_cat")

        mask_cat = pd.Series(True, index=df_cat.index)
        if cat_sel != "Todas" and "categoria" in df_cat.columns:
            mask_cat &= df_cat["categoria"].astype(str) == cat_sel
        if cat_range is not None and len(cat_range) == 2 and "fecha" in df_cat.columns:
            mask_cat &= (df_cat["fecha"].dt.date >= cat_range[0]) & (df_cat["fecha"].dt.date <= cat_range[1])
        df_cat_f = df_cat.loc[mask_cat]

        if len(df_cat_f) == 0:
            st.info("No hay datos para el filtro de categorías seleccionado.")
        else:
            t1, t2 = st.tabs(["Serie temporal", "Por categoría"])
            with t1:
                agg = df_cat_f.groupby("fecha").agg({actual_col: "sum", pred_col: "sum"}).reset_index()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[actual_col], name="Actual", line=dict(color="#94a3b8", width=2)))
                fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[pred_col], name="Predicho", line=dict(color=ACCENT, width=2.5)))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Actual vs predicho (categorías)", height=390)
                st.plotly_chart(fig, use_container_width=True)
            with t2:
                bar = df_cat_f.groupby("categoria").agg({actual_col: "sum", pred_col: "sum"}).reset_index()
                fig = go.Figure()
                fig.add_trace(go.Bar(x=bar["categoria"], y=bar[actual_col], name="Actual", marker_color="#94a3b8"))
                fig.add_trace(go.Bar(x=bar["categoria"], y=bar[pred_col], name="Predicho", marker_color=ACCENT))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Actual vs predicho por categoría", barmode="group", height=420, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
