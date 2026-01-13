import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- ACCESO GOOGLE SHEETS (CAPTURA 1000266173.jpg) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str) == str(u)) & (df['clave'].astype(str) == str(p))]
        return not match.empty
    except: return False

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")
st.markdown("<style>.stApp { background-color: #0B0E11 !important; color: white; } [data-testid='stMetricValue'] { color: #F0B90B !important; }</style>", unsafe_allow_html=True)

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER"):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True; st.session_state.user_name = u
                st.rerun()
            else: st.error("Acceso Denegado")
else:
    # --- MOTOR PREDADOR RESTAURADO ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({'precios_hist': [], 'wallet': 1000.0, 'cosecha': 0.20})

    # SIDEBAR CON 20 MONEDAS (CAPTURA 1000266199.jpg)
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=80)
        monedas = ["SOL/USDT", "BTC/USDT", "ETH/USDT", "ETC/USDT", "BNB/USDT", "FET/USDT", "PEPE/USDT", "DOGE/USDT", "LINK/USDT", "SHIB/USDT", "NEAR/USDT", "WIF/USDT", "ADA/USDT", "RNDR/USDT", "AVAX/USDT", "ORDI/USDT", "SUI/USDT", "DOT/USDT", "FIL/USDT", "XRP/USDT"]
        par = st.selectbox("🎯 Cazar Tendencia:", monedas)
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=False)
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niv = st.number_input("Niveles", 1, 20, 7)
        dist = st.slider("Distancia (%)", 0.01, 1.0, 0.05) / 100
        inv = st.number_input("Inversión USDT", 10.0, 5000.0, 10.0)
        st.divider()
        rsi_in = st.slider("RSI Entrada", 10, 90, 52)
        tp_in = st.slider("Profit Objetivo (%)", 0.001, 0.500, 0.030, format="%.3f")

    # HEADER
    st.markdown(f"## 👁️ H y G Inovaciones - 👤 {st.session_state.user_name}")

    # FETCH PRECIO (REPARADO)
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={par.replace('/', '')}").json()
        precio_act = float(r['price'])
        st.session_state.precios_hist.append(precio_act)
    except: precio_act = 0.0

    # MÉTRICAS (PRECIO, WALLET, COSECHA)
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Precio {par}", f"${precio_act:,.4f}")
    m2.metric("Wallet", f"${st.session_state.wallet:,.2f}")
    if bot_on: st.session_state.cosecha += 0.0001 # Cosecha Agresiva
    m3.metric("Cosecha Total", f"${st.session_
        
