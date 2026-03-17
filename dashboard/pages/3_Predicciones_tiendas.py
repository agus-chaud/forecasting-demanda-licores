"""
Predicciones por tienda.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
from paths import PREDICTIONS_BY_STORE_PARQUET
from theme import ACCENT, inject_theme

st.set_page_config(page_title="Predicciones por tienda | Forecasting Licores", page_icon="🏪", layout="wide")
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
    # Si no existe store_abc, la calculamos con análisis ABC (Pareto)
    if "store_id" in df.columns and "store_abc" not in df.columns:
        sales_col = "actual" if "actual" in df.columns else ("ventas" if "ventas" in df.columns else None)
        if sales_col:
            totals = df.groupby("store_id")[sales_col].sum().sort_values(ascending=False)
            cum_share = totals.cumsum() / totals.sum()
            abc_map = {}
            for store, share in cum_share.items():
                if share <= 0.80:
                    abc_map[store] = "A"
                elif share <= 0.95:
                    abc_map[store] = "B"
                else:
                    abc_map[store] = "C"
            df["store_abc"] = df["store_id"].map(abc_map).fillna("C")
    return df


def draw_tiles(values: list[str], state_key: str, prefix_key: str) -> None:
    if not values:
        st.info("No hay valores para mostrar en tarjetas.")
        return
    # Use unified accent color for all tiles
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

df_store = load_predictions(str(PREDICTIONS_BY_STORE_PARQUET))

st.title("Predicciones por tienda")

if "ventas_store_sel" not in st.session_state:
    st.session_state["ventas_store_sel"] = "Todas"

# Sidebar: filtros de tiendas
with st.sidebar:
    st.subheader("Filtros tiendas")
    tiers = ["Todas"]
    stores = ["Todas"]
    
    # Check if we have tier data internally
    has_tiers = False
    if df_store is not None and not df_store.empty:
        if "store_abc" in df_store.columns:
            has_tiers = True
            tiers += sorted(df_store["store_abc"].dropna().astype(str).unique().tolist())
        if "store_id" in df_store.columns:
            stores += sorted(df_store["store_id"].dropna().astype(str).unique().tolist())
            
    if has_tiers:
        tier_sel = st.selectbox(
            "Tier tienda",
            tiers,
            index=0,
            help=(
                "Clasificación ABC (análisis de Pareto) calculada sobre las ventas reales acumuladas por tienda. "
                "**Tier A**: tiendas que concentran hasta el 80 %% del total de ventas. "
                "**Tier B**: las siguientes que suman entre el 80 %% y 95 %%. "
                "**Tier C**: el resto (bajo volumen). "
                "Permite filtrar rápidamente por peso relativo en el negocio."
            )
        )
        # Efecto cascada guiado por datos comprobados
        if tier_sel != "Todas":
            filtered_df = df_store[df_store["store_abc"].astype(str) == tier_sel]
            if "store_id" in filtered_df.columns:
                stores = ["Todas"] + sorted(filtered_df["store_id"].dropna().astype(str).unique().tolist())
    else:
        tier_sel = "Todas"  # Forzamos valor base para la lógica posterior
        st.selectbox(
            "Tier tienda",
            ["Sin datos"],
            disabled=True,
            help="⚠️ No se encontraron datos de 'store_abc' (Tiers) en el archivo de predicciones actual. Esta columna es necesaria para agrupar las tiendas por volumen/importancia."
        )

    # Prevenimos error si el usuario tenía seleccionada una tienda que no está en el nuevo tier
    if st.session_state["ventas_store_sel"] not in stores:
        st.session_state["ventas_store_sel"] = "Todas"

    store_sel = st.selectbox("Tienda", stores, index=stores.index(st.session_state["ventas_store_sel"]))
    st.session_state["ventas_store_sel"] = store_sel
    store_range = None
    if df_store is not None and not df_store.empty and "fecha" in df_store.columns:
        st_min = df_store["fecha"].min()
        st_max = df_store["fecha"].max()
        store_range = st.date_input("Rango fechas (tiendas)", value=(st_min, st_max), min_value=st_min, max_value=st_max)

if df_store is None or df_store.empty:
    st.warning("No existe el archivo de predicciones por tienda.")
else:
    actual_store_col = "actual" if "actual" in df_store.columns else "ventas"
    pred_store_col = "pred_ensemble" if "pred_ensemble" in df_store.columns else "predicho"

    mask_store = pd.Series(True, index=df_store.index)
    if tier_sel != "Todas" and "store_abc" in df_store.columns:
        mask_store &= df_store["store_abc"].astype(str) == tier_sel
    if store_sel != "Todas" and "store_id" in df_store.columns:
        mask_store &= df_store["store_id"].astype(str) == store_sel
    if store_range is not None and len(store_range) == 2 and "fecha" in df_store.columns:
        mask_store &= (df_store["fecha"].dt.date >= store_range[0]) & (df_store["fecha"].dt.date <= store_range[1])
    df_store_f = df_store.loc[mask_store]

    if len(df_store_f) == 0:
        st.info("No hay datos para el filtro de tiendas seleccionado.")
    else:
        top_stores = (
            df_store_f.groupby("store_id")[actual_store_col]
            .sum()
            .sort_values(ascending=False)
            .head(6)
            .index.astype(str)
            .tolist()
            if "store_id" in df_store_f.columns
            else []
        )
        st.caption(f"{len(df_store_f):,} filas filtradas | Tiendas visibles: {df_store_f['store_id'].nunique() if 'store_id' in df_store_f.columns else 0}")
        draw_tiles(top_stores, "ventas_store_sel", "tile_store")

        t1, t2, t3 = st.tabs(["Serie temporal tiendas", "Por tienda", "Tabla tiendas"])
        with t1:
            agg = df_store_f.groupby("fecha").agg({actual_store_col: "sum", pred_store_col: "sum"}).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[actual_store_col], name="Actual", line=dict(color="#94a3b8", width=2)))
            fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[pred_store_col], name="Predicho", line=dict(color=ACCENT, width=2.5)))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Actual vs predicho (tiendas)", height=390)
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            if "store_id" in df_store_f.columns:
                by_store = (
                    df_store_f.groupby("store_id").agg({actual_store_col: "sum", pred_store_col: "sum"}).reset_index()
                    .sort_values(actual_store_col, ascending=False)
                    .head(20)
                )
                fig = go.Figure()
                fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store[actual_store_col], name="Actual", marker_color="#94a3b8"))
                fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store[pred_store_col], name="Predicho", marker_color=ACCENT))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Top 20 tiendas por ventas", barmode="group", height=420, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay columna `store_id` en el archivo de tiendas.")
        with t3:
            st.dataframe(df_store_f, use_container_width=True)
