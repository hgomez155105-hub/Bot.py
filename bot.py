import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="📈")

# --- FUNCIÓN PARA OBTENER TENDENCIAS DE BINANCE ---
def obtener_top_20_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        # Filtrar solo pares contra USDT y ordenar por volumen
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        # Formatear para el selectbox (ej: BTC/USDT)
        simbolos = [f"{s[:-4]}/USDT" for s in top_20['symbol']]
        return simbolos
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT", "BNB/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

# --- ESTILOS Y LOGO ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .main-header { font-size: 2.5rem; color: #F0B90B; text-align: center; font-weight: bold; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    </style>
    """, unsafe_allow_html=True)

# URL del logo (puedes cambiarla por tu link directo)
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/1991/1991047.png" 

# --- SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image(LOGO_URL, width=100)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            if user_input and pass_input: # Aquí va tu lógica de DB
                st.session_state.autenticado = True
                st.session_state.user_name = user_input
                st.rerun()
else:
    # --- INICIALIZACIÓN DE ESTADOS ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 
            'ultimo_par': "", 'historial_cierres': []
        })

    # --- ENCABEZADO PRINCIPAL ---
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown(f"## 🚀 H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    with head_col2:
        st.image(LOGO_URL, width=50)

    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader("🌐 Mercado en Tendencia")
        monedas_trend = obtener_top_20_binance()
        par = st.selectbox("Seleccionar Activo (Top 20 Binance):", monedas_trend)
        
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
            st.rerun()

        st.divider()
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        st.text_input("API Key", type="password")
        st.text_input("Secret Key", type="password")
        
        st.subheader("⚙️ Estrategia")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 15, 5)
        distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0
