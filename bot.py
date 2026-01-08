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

# --- ESTILO COMPACTO ---
st.set_page_config(page_title="Scalper Bot RSI", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.6rem !important; font-weight: 400 !important; }
    [data-testid="stMetricLabel"] { color: #CCCCCC !important; font-size: 0.85rem !important; }
    .stTable, [data-testid="stTable"] td { color: #FFFFFF !important; font-size: 0.9rem !important; font-weight: 600 !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False
    st.session_state.entrada = 0.0
    st.session_state.stop_fijo = 0.0
if 'moneda_actual' not in st.session_state:
    st.session_state.moneda_actual = "SOL"

# --- SIDEBAR ---
st.sidebar.header("⚙️ Estrategia RSI 30/60")
moneda_nueva = st.sidebar.selectbox("Seleccionar Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])

if moneda_nueva != st.session_state.moneda_actual:
    st.session_state.moneda_actual = moneda_nueva
    st.session_state.comprado = False 
    st.rerun()

monto_trade = 10.0
st.sidebar.info("Compra: RSI < 30\nVenta: RSI > 60")
sl_p = st.sidebar.slider("Stop Loss % (Seguridad)", 0.1, 5.0, 2.0)
encendido = st.sidebar.toggle("🚀 ACTIVAR BOT", value=False)

if st.sidebar.button("🗑️ Limpiar Historial"):
    
