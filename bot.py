import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURACIÓN DE ACCESO (Hojas de Google) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        # Verificación exacta según tu captura 1000266173.jpg
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except: return False

# --- 2. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", initial_sidebar_state="expanded")

# Estilo Negro y Dorado Predador (Captura 1000266162.jpg)
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    .stTable { background-color: #161A1E !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. GESTIÓN DE ESTADO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- 4. INTERFAZ DE LOGIN ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_input, p_input):
                st.session_state.autenticado = True
                st.session_state.user_name = u_input
                st.rerun()
            else:
                st.error("Credenciales incorrectas. Verifique su base de datos.")

# --- 5. MOTOR PREDADOR ACTIVO ---
else:
    # Inicialización de variables de sesión si no existen
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla_data': [], 'historial_pnl': [],
            'wallet': 1000.0, 'cosecha': 0.20, 'ultimo_par': ""
        })

    # SIDEBAR: Panel de Control (Captura 1000266199.jpg)
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=80)
        
        # Las 20 monedas solicitadas en tendencia
        tendencias = [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "ETC/USDT", "BNB/USDT", 
            "FET/USDT", "PEPE/USDT", "DOGE/USDT", "LINK/USDT", "SHIB/USDT",
            "NEAR/USDT", "WIF/USDT", "ADA/USDT", "RNDR/USDT", "AVAX/USDT",
            "ORDI/USDT", "SUI/USDT", "DOT/USDT", "FIL/USDT", "XRP/USDT"
        ]
        par = st.selectbox("🎯 Cazar Tendencia:", tendencias)
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        
        st.markdown("### 🔑 Conexión")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        st.text_input("API Key", type="password")
        st.text_input("Secret Key", type="password")
        
        st.markdown("### ⚙️ Malla")
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niv = st.number_input("Niveles", 1, 20, 7)
        dist = st.slider("Distancia (%)", 0.01, 1.0, 0.05) / 100
        inv = st.number_input("Inversión USDT", 10.0, 5000.0, 10.0)
        
        st.markdown("### 🛠️ Caza Agresiva")
        rsi_in = st.slider("RSI Entrada", 10, 90, 52)
        tp_in = st.slider("Profit Objetivo (%)", 0.001, 0.500, 0.030, format="%.3f")
        
        if st.button("🚨 BOTÓN DE PÁNICO"):
            st.session_state.malla_data = []

    # Reset automático al cambiar de par (Evita que el gráfico se rompa)
    if st.session_state.ultimo_par != par:
        st.session_state.precios_hist = []
        st.session_state.malla_data = []
        st.session_state.ultimo_par = par

    # CABECERA PRINCIPAL
    st.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)

    # OBTENER PRECIO REAL DE BINANCE
    try:
        symbol = par.replace("/", "")
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=2)
        precio_act = float(r.json()['price'])
    except:
        precio_act = st.session_state.precios_hist[-1] if st.session_state.precios_hist else 0.0

    if precio_act > 0:
        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)

        #
        
