import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Elite", layout="centered")

# --- ESTILO MÓVIL (MANTENIDO) ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 10px; text-align: center;
    }
    .metric-label { font-size: 0.7rem; color: #848E9C; font-weight: bold; }
    .metric-value { font-size: 1.1rem; font-weight: bold; color: #F0B90B; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN RSI ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50.0
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_ganancia = np.mean(ganancias[-periodo:])
    avg_perdida = np.mean(perdidas[-periodo:])
    if avg_perdida == 0: return 100.0
    rs = avg_ganancia / avg_perdida
    return 100.0 - (100.0 / (1+rs))

# --- INICIALIZACIÓN ---
if 'ganancia_acumulada' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'saldo_real': 0.0,
        'ganancia_acumulada': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- BARRA LATERAL (CONTROL) ---
with st.sidebar:
    st.markdown("### 🎮 CONTROL CENTRAL")
    modo = st.radio("Entorno de Ejecución:", ["🧪 MODO DEMO", "⚡ MODO REAL (BINANCE)"])
    es_real = modo == "⚡ MODO REAL (BINANCE)"
    
    if es_real:
        with st.expander("🔑 CONFIGURAR API KEYS", expanded=True):
            api_key = st.text_input("Binance API Key", type="password")
            api_secret = st.text_input("Binance Secret Key", type="password")
            # El saldo real se actualizaría aquí con ccxt en producción
            st.session_state.saldo_real = 500.0 

    st.markdown("---")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
    leverage = st.slider("Apalancamiento (x)", 1, 50, 20)
    monto = st.number_input("Inversión por Nivel (USDT)", value=10.0)
    dist_grid = st.slider("Profit Objetivo (%)", 0.05, 2.0, 0.1) / 100
    dist_recompra = 0.5 / 100 # Distancia para abrir niveles hacia abajo

    if st.button("🚨 RESET / CIERRE TOTAL", type="primary"):
        st.session_state.posiciones = []
        st.session_state.ganancia_acumulada = 0.0
        st.rerun()

# --- LÓGICA DE MERCADO ---
st.markdown(f"<h3 style='text-align: center; color: white;'>🚀 {modo}</h3>", unsafe_allow_html=True)
bot_on = st.toggle("ENCENDER ALGORITMO")

if bot_on:
    try:
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)
        
        rsi_actual = calcular_rsi(st.session_state.precios_hist)

        # 1. ENTRADA AGRESIVA (Nivel 1)
        if not st.session_state.posiciones:
            
