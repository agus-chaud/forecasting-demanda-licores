"""
Estilos compartidos para el dashboard tipo tienda de licores.
Inyectar con inject_theme() al inicio de cada página.
"""
import streamlit as st

ACCENT = "#e67e22"
ACCENT_LIGHT = "#f5a623"
BG_DARK = "#1a1a2e"
BG_CARD = "#16213e"
TEXT = "#f5f5f5"
TEXT_MUTED = "#94a3b8"


def inject_theme():
    """Inyecta CSS global: tipografía, botones, cards, fondos."""
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
        <style>
        /* Títulos serif premium */
        h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #f5f5f5 !important; }
        .stMarkdown h1 { font-family: 'Playfair Display', serif !important; }
        /* Botones acento */
        .stButton > button {
            background: linear-gradient(135deg, #e67e22 0%, #d35400 100%) !important;
            color: white !important;
            border: 1px solid #e67e22 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: transform 0.15s, box-shadow 0.15s !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(230, 126, 34, 0.4) !important;
        }
        /* Cards con borde acento */
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
            background: rgba(22, 33, 62, 0.8) !important;
            border: 1px solid rgba(230, 126, 34, 0.3) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
        }
        /* Sidebar más oscuro */
        [data-testid="stSidebar"] { background: #16213e !important; }
        [data-testid="stSidebar"] .stMarkdown { color: #f5f5f5 !important; }
        /* Inputs y selects en tema oscuro */
        .stSelectbox > div > div { background: #16213e !important; }
        .stTextInput > div > div > input { background: #16213e !important; color: #f5f5f5 !important; }
        /* Expander acento */
        .streamlit-expanderHeader { border-left: 3px solid #e67e22 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def category_tile_html(title: str, subtitle: str, accent_color: str = "#e67e22") -> str:
    """Genera HTML para un tile de categoría (estilo imagen tienda)."""
    return f"""
    <div class="cat-tile" style="
        background: linear-gradient(180deg, rgba(0,0,0,0.4) 0%, rgba(22,33,62,0.95) 100%);
        border: 1px solid {accent_color};
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    ">
        <span style="font-family: 'Playfair Display', serif; font-size: 1.4rem; font-weight: 700; color: #fff;">{title}</span>
        <span style="font-size: 0.85rem; color: {accent_color}; margin-top: 0.5rem;">{subtitle}</span>
    </div>
    """


def login_hero_html() -> str:
    """Fondo tipo hero para la pantalla de login."""
    return """
    <div style="
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        z-index: -1;
    "></div>
    <div style="max-width: 420px; margin: 3rem auto; padding: 2rem; background: rgba(22, 33, 62, 0.95); border-radius: 16px; border: 1px solid #e67e22; box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
        <p style="color: #f5f5f5; font-family: 'Playfair Display', serif; font-size: 1.5rem; text-align: center; margin-bottom: 0;">Acceso al dashboard</p>
        <p style="color: #94a3b8; font-size: 0.9rem; text-align: center; margin-top: 0.25rem;">Forecasting Licores</p>
    </div>
    """
