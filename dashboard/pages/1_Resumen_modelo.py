"""
Resumen del modelo: solo XGBoost (mejor modelo), métricas con explicación para negocio.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import check_auth
from paths import MANIFEST_PATH
from theme import inject_theme, ACCENT

st.set_page_config(page_title="Resumen modelo | Forecasting Licores", page_icon="📊", layout="wide")
check_auth()
inject_theme()


@st.cache_data(ttl=300)
def load_manifest(path_str: str) -> dict | None:
    path = Path(path_str)
    if not path.exists():
        return None
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


manifest = load_manifest(str(MANIFEST_PATH))
if manifest is None:
    st.warning(
        "No hay datos del modelo disponibles en este momento. "
        "El equipo de datos actualizará las métricas tras la próxima ejecución del forecasting."
    )
    st.stop()

# Solo métricas del modelo elegido: XGBoost
metrics = manifest.get("metrics", {}).get("XGBoost", {})
if not metrics:
    st.warning("No se encontraron métricas del modelo XGBoost en el último run.")
    st.stop()

st.title("Resumen del modelo")
st.markdown("Bienvenido. Aquí ves el rendimiento del **modelo de predicción de ventas** que usamos para planificar stock y demanda.")

# ----- Card "Modelo en producción" -----
st.markdown(
    f"""
    <div style="
        background: rgba(20, 20, 20, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid #27272A;
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    ">
        <div style="color: #A1A1AA; font-family: 'Inter', sans-serif; font-size: 0.85rem; text-transform: uppercase; font-weight: 600;">Modelo en producción</div>
        <div style="font-family: 'Playfair Display', serif; font-size: 2rem; color: #F8F8F8; margin-top: 0.25rem;">XGBoost</div>
        <div style="color: {ACCENT}; font-family: 'Inter', sans-serif; font-size: 0.95rem; margin-top: 0.25rem;">Mejor equilibrio entre precisión y robustez para predecir ventas por categoría</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----- Definiciones de métricas para negocio (tooltips) -----
METRIC_HELP = {
    "wmape": (
        "**WMAPE** (error porcentual ponderado por ventas)\n\n"
        "Mide cuánto nos equivocamos en las predicciones, dando más peso a las categorías que más venden. "
        "Un valor bajo significa predicciones más fiables para planificar compras y stock."
    ),
    "mape": (
        "**MAPE** (error porcentual medio)\n\n"
        "Error promedio en porcentaje. Ayuda a comparar el rendimiento entre períodos o modelos. "
        "Útil para ver si las predicciones mejoran con el tiempo."
    ),
    "mae": (
        "**MAE** (error absoluto medio en $)\n\n"
        "En promedio, cuántos dólares nos desviamos por predicción. "
        "Sirve para dimensionar el impacto en caja y en inventario."
    ),
    "rmse": (
        "**RMSE** (raíz del error cuadrático medio en $)\n\n"
        "Penaliza más los errores grandes. Un RMSE alto indica que a veces nos equivocamos mucho; "
        "importante para no quedarnos cortos o sobrados en picos de demanda."
    ),
}

# ----- Métricas con explicación: st.metric(help=...) + expander de respaldo -----
st.subheader("Métricas de precisión del modelo")

wmape = metrics.get("wmape")
mape = metrics.get("mape")
mae = metrics.get("mae")
rmse = metrics.get("rmse")

cols = st.columns(4)
items = [
    ("WMAPE", f"{wmape:.1%}" if wmape is not None else "—", "wmape"),
    ("MAPE", f"{mape:.1f}%" if mape is not None else "—", "mape"),
    ("MAE", f"${mae:,.0f}" if mae is not None else "—", "mae"),
    ("RMSE", f"${rmse:,.0f}" if rmse is not None else "—", "rmse"),
]
for i, (label, val_fmt, key) in enumerate(items):
    cols[i].metric(label, val_fmt, help=METRIC_HELP[key])

with st.expander("¿Qué significan estas métricas?"):
    for key in ("wmape", "mape", "mae", "rmse"):
        st.markdown(METRIC_HELP[key])

st.caption("Pasa el cursor sobre el icono ⓘ de cada métrica para ver qué significa. También puedes abrir «¿Qué significan estas métricas?».")

# ----- Contexto del último run (lenguaje negocio) -----
st.subheader("Contexto de la última actualización")
st.write(
    f"- **Período de entrenamiento**: datos hasta {manifest.get('cutoff_train', '—')}"
)
st.write(
    f"- **Período evaluado**: de {manifest.get('cutoff_test_min', '—')} a {manifest.get('cutoff_test_max', '—')}"
)
st.write(
    f"- **Predicciones generadas**: {manifest.get('n_predictions', '—'):,} registros (ventas por categoría y fecha)"
)
