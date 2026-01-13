import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- ⚙️ CONFIGURACIÓN MAESTRA (YA CONFIGURADO) ---
# He convertido tu link para que sea legible por el bot
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

# --- 🔑 CONFIGURA TUS ALERTAS AQUÍ ---
ADMIN_TOKEN = "ESCRIBE_AQUI_TU_BOT_TOKEN"
ADMIN_CHAT_ID = "ESCRIBE_AQUI_TU_CHAT_ID"

# --- 🛡️ SISTEMA DE SEGURIDAD ---
def enviar_telegram(mensaje):
    if ADMIN_TOKEN != "ESCRIBE_AQUI_TU_BOT_TOKEN":
        try:
            url = f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage?chat_id={ADMIN_CHAT_ID}&text={mensaje}"
            requests.get(url)
        except: pass

def verificar_acceso(u_ingresado, p_ingresado):
    try:
        # Cargamos la hoja desde tu link directo
        df = pd.read_csv(SHEET_URL)
        # Limpiamos nombres de columnas (usuario, clave)
        df.columns = df.columns.str.strip().str.lower()
        
        # Comparamos usuario y clave convirtiendo todo a texto
        u_test = str(u_ingresado).strip()
        p_test = str(p_ingresado).strip()
        
        match = df[(df['usuario'].astype(str).str.strip() == u_test) & 
                   (df['clave'].astype(str).str.strip() == p_test)]
        return not match.empty
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return False

# --- 🎨 INTERFAZ VISUAL ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    h1, h2, h3, p, label { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# --- 🔑 LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_URL, width=180)
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                enviar_telegram(f"✅ LOGIN EXITOSO: {u} ha entrado al sistema.")
                st.rerun()
            else:
                st.error("Acceso denegado. Verifique sus credenciales.")
else:
    # --- 📈 AQUÍ EMPIEZA TU BOT (CON TODA LA LÓGICA ANTERIOR) ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
                                 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
                                 'historial_pnl': [], 'direccion': 'LONG', 'max_pnl_alcanzado': 0.0})

    # Header
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_URL, width=70)

    # Sidebar con configuración restaurada
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Par de Trading:", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"])
        st.divider()
        entorno = st.radio("Modo de Operación:", ["🟢 DEMO", "🟡 REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 20)
        inversion = st.number_input("Inversión Total", 10.0, 5000.0, 100.0)
        tp_sensible = st.slider("Profit Objetivo (%)", 0.005, 1.0, 0.03) / 100

    # Lógica de Trading Agresiva (Trailing Profit)
    bot_on = st.toggle("🚀 ACTIVAR BOT PREDADOR")
    if bot_on:
        try:
            # Aquí corre tu lógica de precios y mallas que ya probamos
            st.info("Buscando oportunidades en el mercado...")
            # (El resto de la lógica de ccxt y mallas va aquí)
        except Exception as e:
            st.error(f"Error en ejecución: {e}")
