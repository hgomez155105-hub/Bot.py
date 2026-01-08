import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- SEGURIDAD ---
PASSWORD = "caseros2024"
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if clave == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# --- ESTILO DE ALTO CONTRASTE (BLANCO PURO Y BRILLANTE) ---
st.set_page_config(page_title="Scalper Pro Dashboard", layout="wide")
st.markdown("""
    <style>
    /* Fondo negro profundo */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Métricas: Texto blanco brillante */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 2rem !important; 
        font-weight: 800 !important;
        text-shadow: 0px 0px 5px rgba(255,255,255,0.2);
    }
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-size: 1rem !important; 
        font-weight: 700 !important;
        text-transform: uppercase;
    }
    
    /* Contenedores de métricas */
    div[data-testid="metric-container"] { 
        background-color: #111111; border: 2px solid #444; border-radius: 12px; padding: 12px; 
    }

    /* --- CORRECCIÓN DE TABLA: BLANCO BRILLANTE --- */
    .stTable, [data-testid="stTable"] td, [data-testid="stTable"] th { 
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
        font-weight: 700 !important; 
        border-bottom: 1px solid #444 !important;
        opacity: 1 !important;
    }
    
    /* Títulos blancos */
    h1, h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state: st.session_state.saldo = 1000.0
if 'ganancia_total' not in st.session_state: st.session_state.ganancia_total = 0.0
if 'perdida_total' not in st.session_state: st.session_state.perdida_total = 0.0
if 'trades_exitosos' not in st.session_state: st.session_state.trades_exitosos = 0
if 'total_trades' not in st.session_state: st.session_state.total_trades = 0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Resultado", "Billetera"])
if 'comprado' not in st.session_state: st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("⚙️ CONFIGURACIÓN")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_trade = st.sidebar.number_input("Monto Trade (USD):", value
                                      
