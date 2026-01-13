import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN ADMIN (Pon tus datos aquí y no se borrarán) ---
ADMIN_TOKEN = "TU_TOKEN_AQUÍ"
ADMIN_CHAT_ID = "TU_CHAT_ID_AQUÍ"
# Tu URL de Google Sheets terminada en export?format=csv
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA/export?format=csv"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- FUNCIONES DE SEGURIDAD ---
def enviar_telegram(mensaje):
    if ADMIN_TOKEN != "TU_TOKEN_AQUÍ":
        try:
            url = f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage?chat_id={ADMIN_CHAT_ID}&text={mensaje}"
            requests.get(url)
        except: pass

def verificar_credenciales(u, p):
    try:
        df_users = pd.read_csv(SHEET_URL)
        # Limpieza de datos para evitar errores de lectura
        df_users.columns = df_users.columns.str.strip().str.lower()
        u_limpio = str(u).strip()
        p_limpio = str(p).strip()
        
        user_match = df_users[(df_users['usuario'].astype(str) == u_limpio) & 
                              (df_users['password'].astype(str) == p_limpio)]
        return not user_match.empty
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        return False

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    h1, h2, h3, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# --- LÓGICA DE ACCESO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_credenciales(u_input, p_input):
                st.session_state.autenticado = True
                st.session_state.user_name = u_input
                enviar_telegram(f"✅ Acceso exitoso: {u_input}")
                st.rerun()
            else:
                st.error("Credenciales incorrectas. Verifique su base de datos.")
else:
    # --- INTERFAZ DEL BOT (RESTAURADA COMPLETA) ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
                                 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
                                 'historial_pnl': [], 'direccion': 'LONG', 'max_pnl_alcanzado': 0.0})

    # Header
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_URL, width=70)

    # Sidebar (RESTAURADO MODO DEMO/REAL)
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Objetivo Binance:", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        st.divider()
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 50, 10)
        distancia = st.slider("Distancia (%)", 0.01, 1.0, 0.2) / 100
        inversion = st.number_input("Inversión (USDT)", 10.0, 10000.0, 100.0)
        tp_sensible = st.slider("Profit (%)", 0.005, 1.0, 0.03, format="%.3f") / 100

    # Lógica de Trading (RESTAURADA AGRESIVA)
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            # Captura de precio real
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            
            # --- Lógica de Trailing Profit (Para seguir las subidas) ---
            if st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                pnl = ((precio_act / p_prom - 1) if st.session_state.direccion == "LONG" else (1 - precio_act / p_prom)) * t_inv * lev
                
                if pnl >= (t_inv * tp_sensible * lev):
                    if pnl > st.session_state.max_pnl_alcanzado: st.session_state.max_pnl_alcanzado = pnl
                    if pnl < (st.session_state.max_pnl_alcanzado * 0.97): # Cierre al retroceder
                        enviar_telegram(f"💰 ¡GANANCIA! {st.session_state.user_name} cobró ${round(pnl, 2)}")
                        st.session_state.ganancia_total += pnl
                        st.session_state.update({'posiciones': [], 'ordenes_malla': [], 'max_pnl_alcanzado': 0.0})
                        st.rerun()

            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Precio", f"${precio_act:,.4f}")
            c2.metric("Saldo", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("Total", f"${st.session_state.ganancia_total:,.2f}")

            time.sleep(1); st.rerun()
        except: time.sleep(5); st.rerun()
        
