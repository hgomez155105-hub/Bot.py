import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN BASE (LOGIN) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except: return False

st.set_page_config(page_title="H y G Inovaciones", layout="wide")

# --- ESTILO PREDADOR ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        u_in = st.text_input("Usuario")
        p_in = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_in, p_in):
                st.session_state.autenticado = True
                st.session_state.user_name = u_in
                st.rerun()
            else: st.error("Acceso denegado.")
else:
    # --- MOTOR AGRESIVO REPARADO ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla_data': [], 'historial_pnl': [],
            'wallet': 1000.0, 'cosecha': 0.20, 'ultimo_par': ""
        })

    # SIDEBAR: Panel de Control (Como en tus fotos)
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=80)
        par = st.selectbox("🎯 Objetivo Binance:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"], index=0)
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        
        st.markdown("### 🔑 Conexión Exchange")
        modo = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        
        st.markdown("### ⚙️ Configuración de Malla")
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niv = st.number_input("Cantidad de Niveles", 1, 20, 7)
        dist = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05) / 100
        inv = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 10.0)
        
        st.markdown("### 🛠️ Caza Agresiva")
        rsi_in = st.slider("RSI Entrada", 10, 90, 52)
        tp_in = st.slider("Profit Objetivo (%)", 0.001, 0.500, 0.030, format="%.3f")
        
        if st.button("🚨 BOTÓN DE PÁNICO"):
            st.session_state.malla_data = []

    # Reset si cambia la moneda para que el gráfico no haga cosas raras
    if st.session_state.ultimo_par != par:
        st.session_state.precios_hist = []
        st.session_state.malla_data = []
        st.session_state.ultimo_par = par

    # HEADER
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"## 👁️ H y G Inovaciones - <span class='user
