"""
Estilos compartidos para el dashboard tipo tienda de licores.
Inyectar con inject_theme() al inicio de cada página.
"""
import streamlit as st

ACCENT = "#D9A05B"
ACCENT_SECONDARY = "#8C2E2A"
BG_DARK = "#0A0A0A"
BG_CARD = "#141414"
TEXT = "#F8F8F8"
TEXT_MUTED = "#A1A1AA"
BORDER = "#27272A"
SUCCESS = "#10B981"
DANGER = "#EF4444"

def inject_theme():
    """Inyecta CSS global: tipografía, botones, cards, fondos."""
    # Leer e inyectar CSS externo
    import os
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )


def category_tile_html(title: str, subtitle: str, accent_color: str = "#D9A05B") -> str:
    """Genera HTML para un tile de categoría (estilo imagen tienda)."""
    return f"""
    <div class="cat-tile" style="
        background: rgba(20, 20, 20, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid #27272A;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
        <span style="font-family: 'Playfair Display', serif; font-size: 1.4rem; font-weight: 700; color: #F8F8F8;">{title}</span>
        <span style="font-family: 'Inter', sans-serif; font-size: 0.85rem; color: {accent_color}; margin-top: 0.5rem;">{subtitle}</span>
    </div>
    """


def login_hero_html() -> str:
    """Fondo tipo hero para la pantalla de login."""
    return """
    <div style="
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: #0A0A0A;
        z-index: -1;
    "></div>
    <div style="max-width: 420px; margin: 3rem auto; padding: 2rem; background: rgba(20, 20, 20, 0.6); backdrop-filter: blur(12px); border-radius: 16px; border: 1px solid #27272A; box-shadow: 0 8px 32px rgba(0,0,0,0.5);">
        <p style="color: #F8F8F8; font-family: 'Playfair Display', serif; font-size: 1.75rem; text-align: center; margin-bottom: 0;">Acceso al dashboard</p>
        <p style="color: #A1A1AA; font-family: 'Inter', sans-serif; font-size: 0.95rem; text-align: center; margin-top: 0.25rem;">Forecasting Licores</p>
    </div>
    """

