"""Autenticación para el dashboard. Credenciales vía st.secrets (usuario, password)."""
import os
import streamlit as st


def inject_login_theme():
    """Fondo y estilo tipo tienda de licores para la pantalla de login."""
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
        <style>
        section.main .block-container { padding-top: 3rem; }
        [data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
        </style>
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <p style="color: #f5f5f5; font-family: 'Playfair Display', serif; font-size: 1.75rem; margin: 0;">Acceso al dashboard</p>
            <p style="color: #94a3b8; font-size: 0.95rem; margin-top: 0.25rem;">Forecasting Licores</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_credentials():
    """Obtiene usuario y contraseña desde secrets o variables de entorno."""
    try:
        u = st.secrets.get("usuario") or os.environ.get("DASHBOARD_USUARIO", "")
        p = st.secrets.get("password") or os.environ.get("DASHBOARD_PASSWORD", "")
        return u, p
    except Exception:
        return os.environ.get("DASHBOARD_USUARIO", ""), os.environ.get("DASHBOARD_PASSWORD", "")


def check_auth():
    """
    Si el usuario no está autenticado, muestra el formulario de login y hace st.stop().
    Llamar al inicio de app.py y de cada página.
    """
    if st.session_state.get("authenticated"):
        return
    user_expected, pass_expected = get_credentials()
    if not user_expected or not pass_expected:
        st.warning("Configura usuario y contraseña en Secrets (usuario, password) o en variables DASHBOARD_USUARIO y DASHBOARD_PASSWORD.")
        st.stop()
    inject_login_theme()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            usuario = st.text_input("Usuario", key="login_user", placeholder="Tu usuario")
            password = st.text_input("Contraseña", type="password", key="login_pass", placeholder="Tu contraseña")
            if st.form_submit_button("Entrar"):
                if usuario == user_expected and password == pass_expected:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = usuario
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()
