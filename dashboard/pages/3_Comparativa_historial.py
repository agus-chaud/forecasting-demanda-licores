"""
Comparativa e historial: tabla con estilo oscuro, evolución WMAPE con Plotly (tema oscuro, acento en último run).
Carga: artifacts/modeling/experiments_history.csv
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
from paths import HISTORY_PATH
from theme import inject_theme, ACCENT

st.set_page_config(page_title="Comparativa e historial | Forecasting Licores", page_icon="📉", layout="wide")
check_auth()
inject_theme()


@st.cache_data(ttl=300)
def load_history(path_str: str) -> pd.DataFrame | None:
    path = Path(path_str)
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "run_ts" in df.columns:
        df["run_ts"] = pd.to_datetime(df["run_ts"], errors="coerce")
    return df


df = load_history(str(HISTORY_PATH))
if df is None or df.empty:
    st.warning(
        f"No se encontró historial en `{HISTORY_PATH}`. Ejecuta el notebook de forecasting para generarlo."
    )
    st.stop()

st.title("Comparativa e historial de experimentos")
st.caption(f"{len(df)} ejecuciones")

# Tabla (Streamlit dataframe con tema heredado)
st.subheader("Tabla de runs")
st.dataframe(df, use_container_width=True)

# Gráfico evolución WMAPE con Plotly tema oscuro
wmape_cols = [c for c in df.columns if "wmape" in c.lower()]
if wmape_cols:
    st.subheader("Evolución de WMAPE por run")
    x_col = "run_ts" if "run_ts" in df.columns else "experiment_id"
    if x_col not in df.columns and len(df.columns) > 0:
        x_col = df.columns[0]
    x_vals = df[x_col].astype(str).tolist()
    # Una serie por columna WMAPE; último punto en acento
    fig = go.Figure()
    for wcol in wmape_cols:
        fig.add_trace(
            go.Scatter(
                x=x_vals, y=df[wcol],
                name=wcol.replace("wmape_", "").replace("_", " ").title(),
                line=dict(color=ACCENT, width=2),
                mode="lines+markers",
            )
        )
    # Resaltar último punto
    if len(x_vals) > 0 and wmape_cols:
        last_y = df[wmape_cols[0]].iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=[x_vals[-1]], y=[last_y],
                name="Último run",
                mode="markers",
                marker=dict(size=14, color=ACCENT, symbol="diamond", line=dict(width=2, color="#fff")),
                showlegend=True,
            )
        )
    fig.update_layout(
        paper_bgcolor="rgba(22, 33, 62, 0.9)",
        plot_bgcolor="rgba(22, 33, 62, 0.5)",
        font=dict(color="#f5f5f5", size=12),
        xaxis=dict(gridcolor="rgba(245,245,245,0.1)", zerolinecolor="rgba(245,245,245,0.2)"),
        yaxis=dict(gridcolor="rgba(245,245,245,0.1)", zerolinecolor="rgba(245,245,245,0.2)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        height=400,
        margin=dict(t=40, b=80, l=50, r=30),
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay columnas WMAPE en el historial para graficar.")

# Último run destacado (expander con borde acento)
if "run_ts" in df.columns:
    df_sorted = df.sort_values("run_ts", ascending=False)
    ultimo = df_sorted.iloc[0]
    st.markdown(
        f'<div style="border-left: 4px solid {ACCENT}; padding-left: 1rem; margin-top: 1rem;">',
        unsafe_allow_html=True,
    )
    with st.expander("Último run (detalle)"):
        st.json(ultimo.to_dict())
    st.markdown("</div>", unsafe_allow_html=True)
