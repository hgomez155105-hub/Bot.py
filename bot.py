import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN DE BASE DE DATOS (GOOGLE SHEETS) ---
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
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# --- LOGIN ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        u_in = st.text_input("Usuario")
        p_in = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_input, p_input): # Validación real contra Sheets
                st.session_state.autenticado = True
                st.session_state.user_name = u_in
                st.rerun()
            else: st.error("Acceso denegado")
else:
    # --- MOTOR AGRESIVO ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
            'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
            'historial_pnl': [], 'direccion': 'LONG', 'max_pnl_alcanzado': 0.0
        })

    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=100)
        # 20 MONEDAS EN TENDENCIA
        monedas = ["BTC/USDT", "SOL/USDT", "ETH/USDT", "ETC/USDT", "PEPE/USDT", "DOGE/USDT", "FET/USDT"]
        par = st.selectbox("🎯 Objetivo Binance:", monedas)
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True) # INICIO AGRESIVO
        
        st.divider()
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niveles = st.number_input("Niveles", 1, 50, 10)
        distancia = st.slider("Distancia (%)", 0.01, 1.0, 0.05) / 100
        inversion = st.number_input("Inversión USDT", 10.0, 10000.0, 100.0)
        tp_sensible = st.slider("Profit Objetivo (%)", 0.005, 1.0, 0.030, format="%.3f") / 100

    # LÓGICA DE ACTUALIZACIÓN CONSTANTE
    try:
        # Forzar obtención de precio para que NUNCA esté vacío
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
        precio_act = float(res['USD'])
        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # UI PRINCIPAL (FOTO 1000266162.jpg)
        st.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Precio {par}", f"${precio_act:,.4f}")
        c2.metric("Wallet Balance", f"${st.session_state.saldo_demo:,.2f}")
        c3.metric("PNL Total", f"${st.session_state.ganancia_total:,.2f}")

        # GRÁFICO SIEMPRE VIVO
        fig = go.Figure(go.Scatter(y=st.session_state.precios_hist, line=dict(color='#F0B90B', width=3)))
        fig.update_layout(height=350, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

        # TABLAS
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("📋 Malla de Operación")
            if not st.session_state.ordenes_malla:
                st.session_state.ordenes_malla = [{'id': i+1, 'precio': round(precio_act*(1-(i*distancia)),4), 'monto': inversion/niveles, 'estado': 'PENDIENTE'} for i in range(niveles)]
            st.dataframe(st.session_state.ordenes_malla, use_container_width=True)
        with col_b:
            st.subheader("📜 Historial PNL")
            st.dataframe(st.session_state.historial_pnl, use_container_width=True)

        if bot_on:
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Reiniciando motor... {e}")
        time.sleep(2)
        st.rerun()
