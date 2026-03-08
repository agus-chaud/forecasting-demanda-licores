"""
Dashboard Forecasting Licores — Punto de entrada.
Login por usuario/contraseña; tras autenticación redirige a Resumen del modelo.
"""
import streamlit as st

from auth import check_auth
from theme import inject_theme

st.set_page_config(page_title="Forecasting Licores", page_icon="📊", layout="wide")

check_auth()
inject_theme()

# Tras login, ir directo a Resumen del modelo (sin página intermedia "app")
st.switch_page("pages/1_Resumen_modelo.py")
