"""
Ventas y predicciones:
- Bloque A: categorías de producto.
- Bloque B: tiendas.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
import paths as p
from theme import ACCENT, inject_theme

st.set_page_config(page_title="Ventas y predicciones | Forecasting Licores", page_icon="📈", layout="wide")
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
    colors = ["#e67e22", "#c2410c", "#b45309", "#a16207", "#92400e", "#78350f"]
    row1 = st.columns(3)
    row2 = st.columns(3)
    for i, val in enumerate(values[:6]):
        col = row1[i % 3] if i < 3 else row2[i % 3]
        with col:
            color = colors[i % len(colors)]
            short = val[:26] + "..." if len(val) > 26 else val
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(22,33,62,0.95) 100%);
                    border: 1px solid {color};
                    border-radius: 12px;
                    padding: 1.1rem;
                    text-align: center;
                    margin-bottom: 0.5rem;">
                    <div style="font-family: 'Playfair Display', serif; font-size: 1.05rem; font-weight: 700; color: #fff;">{short}</div>
                    <div style="font-size: 0.8rem; color: {color}; margin-top: 0.35rem;">Ver predicciones</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Ver", key=f"{prefix_key}_{i}", type="primary"):
                st.session_state[state_key] = val
                st.rerun()


def get_common_entities(
    df_hist: pd.DataFrame,
    df_future: pd.DataFrame | None,
    entity_col: str,
) -> set[str] | None:
    """Retorna entidades comunes entre histórico y futuro para comparar en el mismo universo."""
    if df_future is None or df_future.empty:
        return None
    if entity_col not in df_hist.columns or entity_col not in df_future.columns:
        return None
    hist_ids = set(df_hist[entity_col].dropna().astype(str).unique().tolist())
    fut_ids = set(df_future[entity_col].dropna().astype(str).unique().tolist())
    common = hist_ids.intersection(fut_ids)
    return common if common else None


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

PREDICTIONS_PARQUET = p.PREDICTIONS_PARQUET
PREDICTIONS_CSV = p.PREDICTIONS_CSV
PREDICTIONS_BY_STORE_PARQUET = p.PREDICTIONS_BY_STORE_PARQUET
_pred_dir = PREDICTIONS_PARQUET.parent
FUTURE_CATEGORIES_PARQUET = getattr(p, "FUTURE_CATEGORIES_PARQUET", _pred_dir / "forecasting_future_categories.parquet")
FUTURE_STORES_PARQUET = getattr(p, "FUTURE_STORES_PARQUET", _pred_dir / "forecasting_future_stores.parquet")

df_cat = load_predictions(str(PREDICTIONS_PARQUET), str(PREDICTIONS_CSV))
df_store = load_predictions(str(PREDICTIONS_BY_STORE_PARQUET))
df_cat_future = load_predictions(str(FUTURE_CATEGORIES_PARQUET))
df_store_future = load_predictions(str(FUTURE_STORES_PARQUET))

st.title("Ventas y predicciones")

if "ventas_cat_sel" not in st.session_state:
    st.session_state["ventas_cat_sel"] = "Todas"
if "ventas_store_sel" not in st.session_state:
    st.session_state["ventas_store_sel"] = "Todas"

# Sidebar: filtros separados por bloque
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

    st.divider()
    st.subheader("Filtros tiendas")
    tiers = ["Todas"]
    stores = ["Todas"]
    if df_store is not None and not df_store.empty:
        if "store_abc" in df_store.columns:
            tiers += sorted(df_store["store_abc"].dropna().astype(str).unique().tolist())
        if "store_id" in df_store.columns:
            stores += sorted(df_store["store_id"].dropna().astype(str).unique().tolist())
    tier_sel = st.selectbox("Tier tienda", tiers, index=0)
    store_sel = st.selectbox("Tienda", stores, index=stores.index(st.session_state["ventas_store_sel"]) if st.session_state["ventas_store_sel"] in stores else 0)
    st.session_state["ventas_store_sel"] = store_sel
    store_range = None
    if df_store is not None and not df_store.empty and "fecha" in df_store.columns:
        st_min = df_store["fecha"].min()
        st_max = df_store["fecha"].max()
        store_range = st.date_input("Rango fechas (tiendas)", value=(st_min, st_max), min_value=st_min, max_value=st_max)

# BLOQUE A: categorías de producto
st.markdown("### Predicciones por categoría de producto")
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
            common_cats = get_common_entities(df_cat_f, df_cat_future, "categoria")
            if common_cats is not None:
                df_cat_f = df_cat_f[df_cat_f["categoria"].astype(str).isin(common_cats)]

            t1, t2 = st.tabs(["Serie temporal", "Por categoría"])
            with t1:
                if len(df_cat_f) == 0:
                    st.info("No hay categorías comunes entre histórico y forecast futuro para el filtro actual.")
                else:
                    agg = df_cat_f.groupby("fecha").agg({actual_col: "sum", pred_col: "sum"}).reset_index()
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[actual_col], name="Historico", line=dict(color="#94a3b8", width=2)))
                    fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[pred_col], name="Prediccion", line=dict(color=ACCENT, width=2.5)))
                    if df_cat_future is not None and not df_cat_future.empty:
                        fut_mask = pd.Series(True, index=df_cat_future.index)
                        if cat_sel != "Todas" and "categoria" in df_cat_future.columns:
                            fut_mask &= df_cat_future["categoria"].astype(str) == cat_sel
                        if common_cats is not None and "categoria" in df_cat_future.columns:
                            fut_mask &= df_cat_future["categoria"].astype(str).isin(common_cats)
                        fut_col = "pred_ensemble" if "pred_ensemble" in df_cat_future.columns else "predicho"
                        df_cat_future_f = df_cat_future.loc[fut_mask]
                        if len(df_cat_future_f) > 0 and {"fecha", fut_col}.issubset(df_cat_future_f.columns):
                            fut_agg = df_cat_future_f.groupby("fecha")[fut_col].sum().reset_index()
                            fig.add_trace(
                                go.Scatter(
                                    x=fut_agg["fecha"],
                                    y=fut_agg[fut_col],
                                    name="Prediccion futura",
                                    line=dict(color="#f59e0b", width=2.5, dash="dash"),
                                )
                            )
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Historico vs prediccion (categorías)", height=390)
                    st.plotly_chart(fig, use_container_width=True)
                    if common_cats is not None:
                        st.caption(f"Comparación alineada en categorías comunes: {len(common_cats)}")
            with t2:
                if len(df_cat_f) == 0:
                    st.info("No hay categorías comunes para mostrar barras.")
                else:
                    bar = df_cat_f.groupby("categoria").agg({actual_col: "sum", pred_col: "sum"}).reset_index()
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=bar["categoria"], y=bar[actual_col], name="Historico", marker_color="#94a3b8"))
                    fig.add_trace(go.Bar(x=bar["categoria"], y=bar[pred_col], name="Prediccion", marker_color=ACCENT))
                    if df_cat_future is not None and not df_cat_future.empty and "categoria" in df_cat_future.columns:
                        fut_col = "pred_ensemble" if "pred_ensemble" in df_cat_future.columns else "predicho"
                        fut_mask = pd.Series(True, index=df_cat_future.index)
                        if cat_sel != "Todas":
                            fut_mask &= df_cat_future["categoria"].astype(str) == cat_sel
                        if common_cats is not None:
                            fut_mask &= df_cat_future["categoria"].astype(str).isin(common_cats)
                        df_cat_future_f = df_cat_future.loc[fut_mask]
                        if len(df_cat_future_f) > 0 and fut_col in df_cat_future_f.columns:
                            fut_bar = (
                                df_cat_future_f.groupby("categoria")[fut_col]
                                .sum()
                                .reset_index()
                                .rename(columns={fut_col: "prediccion_futura"})
                            )
                            bar = bar.merge(fut_bar, on="categoria", how="outer").fillna(0.0)
                            fig = go.Figure()
                            fig.add_trace(go.Bar(x=bar["categoria"], y=bar[actual_col], name="Historico", marker_color="#94a3b8"))
                            fig.add_trace(go.Bar(x=bar["categoria"], y=bar[pred_col], name="Prediccion", marker_color=ACCENT))
                            fig.add_trace(go.Bar(x=bar["categoria"], y=bar["prediccion_futura"], name="Prediccion futura", marker_color="#f59e0b"))
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Historico vs prediccion por categoría", barmode="group", height=420, xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

st.divider()

# BLOQUE B: tiendas
st.markdown("### Predicciones por tienda")
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
        common_stores = get_common_entities(df_store_f, df_store_future, "store_id")
        if common_stores is not None:
            df_store_f = df_store_f[df_store_f["store_id"].astype(str).isin(common_stores)]

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

        t1, t2 = st.tabs(["Serie temporal tiendas", "Por tienda"])
        with t1:
            if len(df_store_f) == 0:
                st.info("No hay `store_id` comunes entre histórico y forecast futuro para el filtro actual.")
            else:
                agg = df_store_f.groupby("fecha").agg({actual_store_col: "sum", pred_store_col: "sum"}).reset_index()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[actual_store_col], name="Historico", line=dict(color="#94a3b8", width=2)))
                fig.add_trace(go.Scatter(x=agg["fecha"], y=agg[pred_store_col], name="Prediccion", line=dict(color=ACCENT, width=2.5)))
                if df_store_future is not None and not df_store_future.empty:
                    fut_mask = pd.Series(True, index=df_store_future.index)
                    if tier_sel != "Todas" and "store_abc" in df_store_future.columns:
                        fut_mask &= df_store_future["store_abc"].astype(str) == tier_sel
                    if store_sel != "Todas" and "store_id" in df_store_future.columns:
                        fut_mask &= df_store_future["store_id"].astype(str) == store_sel
                    if common_stores is not None and "store_id" in df_store_future.columns:
                        fut_mask &= df_store_future["store_id"].astype(str).isin(common_stores)
                    fut_col = "pred_ensemble" if "pred_ensemble" in df_store_future.columns else "predicho"
                    df_store_future_f = df_store_future.loc[fut_mask]
                    if len(df_store_future_f) > 0 and {"fecha", fut_col}.issubset(df_store_future_f.columns):
                        fut_agg = df_store_future_f.groupby("fecha")[fut_col].sum().reset_index()
                        fig.add_trace(
                            go.Scatter(
                                x=fut_agg["fecha"],
                                y=fut_agg[fut_col],
                                name="Prediccion futura",
                                line=dict(color="#f59e0b", width=2.5, dash="dash"),
                            )
                        )
                fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Historico vs prediccion (tiendas)", height=390)
                st.plotly_chart(fig, use_container_width=True)
                if common_stores is not None:
                    st.caption(f"Comparación alineada en `store_id` comunes: {len(common_stores)}")
        with t2:
            if "store_id" in df_store_f.columns:
                by_store = (
                    df_store_f.groupby("store_id").agg({actual_store_col: "sum", pred_store_col: "sum"}).reset_index()
                    .sort_values(actual_store_col, ascending=False)
                    .head(20)
                )
                fig = go.Figure()
                fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store[actual_store_col], name="Historico", marker_color="#94a3b8"))
                fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store[pred_store_col], name="Prediccion", marker_color=ACCENT))
                if df_store_future is not None and not df_store_future.empty and "store_id" in df_store_future.columns:
                    fut_col = "pred_ensemble" if "pred_ensemble" in df_store_future.columns else "predicho"
                    fut_mask = pd.Series(True, index=df_store_future.index)
                    if tier_sel != "Todas" and "store_abc" in df_store_future.columns:
                        fut_mask &= df_store_future["store_abc"].astype(str) == tier_sel
                    if store_sel != "Todas":
                        fut_mask &= df_store_future["store_id"].astype(str) == store_sel
                    if common_stores is not None:
                        fut_mask &= df_store_future["store_id"].astype(str).isin(common_stores)
                    df_store_future_f = df_store_future.loc[fut_mask]
                    if len(df_store_future_f) > 0 and fut_col in df_store_future_f.columns:
                        fut_by_store = (
                            df_store_future_f.groupby("store_id")[fut_col]
                            .sum()
                            .reset_index()
                            .rename(columns={fut_col: "prediccion_futura"})
                        )
                        by_store = by_store.merge(fut_by_store, on="store_id", how="outer").fillna(0.0)
                        by_store = by_store.sort_values(actual_store_col, ascending=False).head(20)
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store[actual_store_col], name="Historico", marker_color="#94a3b8"))
                        fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store[pred_store_col], name="Prediccion", marker_color=ACCENT))
                        fig.add_trace(go.Bar(x=by_store["store_id"].astype(str), y=by_store["prediccion_futura"], name="Prediccion futura", marker_color="#f59e0b"))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"], title="Top 20 tiendas por ventas", barmode="group", height=420, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay columna `store_id` en el archivo de tiendas.")
