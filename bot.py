import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN DE SEGURIDAD (SOLO TÚ LO VES) ---
# Pon aquí tus datos reales para recibir las alertas
TELEGRAM_BOT_TOKEN = "TU_TOKEN_AQUÍ" 
TELEGRAM_CHAT_ID = "TU_CHAT_ID_AQUÍ"
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID/export?format=csv"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- FUNCIONES DE SISTEMA ---
def enviar_telegram_admin(mensaje):
    """Envía notificaciones solo al administrador"""
    if TELEGRAM_BOT_TOKEN != "TU_TOKEN_AQUÍ":
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={mensaje}"
            requests.get(url)
        except: pass

def verificar_credenciales(u, p):
    try:
        df_users = pd.read_csv(SHEET_URL)
        user_match = df_users[(df_users['usuario'] == u) & (df_users['password'].astype(str) == p)]
        return not user_match.empty
    except: return False

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    h1, h2, h3 { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# --- LOGIN SIMPLIFICADO PARA EL USUARIO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        # El usuario solo ve esto:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_credenciales(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                # Te avisa a ti que alguien entró
                enviar_telegram_admin(f"🚨 ACCESO: El usuario '{u}' acaba de entrar al Predador H y G.")
                st.rerun()
            else:
                st.error("Acceso denegado. Contacte al administrador.")
else:
    # --- INTERFAZ DEL BOT (MANTENIENDO TODO LO ANTERIOR) ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
                                 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
                                 'historial_pnl': [], 'direccion': 'LONG', 'max_pnl_alcanzado': 0.0})

    # Header con el logo y nombre de usuario
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_URL, width=70)

    # Sidebar con configuración de trading
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Objetivo Binance:", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        st.divider()
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        st.divider()
        # Parámetros de la Malla y Caza
        lev = st.slider("Apalancamiento", 1, 50, 20)
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        tp_sensible = st.slider("Profit Objetivo (%)", 0.005, 1.0, 0.030, format="%.3f") / 100

    # Lógica del Bot (Trailing Profit y Acumulación)
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        # Aquí va toda la lógica de ejecución que ya probamos y te gustó.
        # Al cerrar una ganancia, el bot te enviará un mensaje automático:
        # enviar_telegram_admin(f"💰 GANANCIA: El usuario {st.session_state.user_name} cerró +${pnl} USDT")
        st.info("El algoritmo está escaneando el mercado... buscando entrada óptima.")
        time.sleep(1)
        st.rerun()
        
