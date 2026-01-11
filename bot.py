import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="centered")

# --- ENLACE DE TU BASE DE DATOS (REEMPLAZA ESTE LINK) ---
LINK_DB = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT_tu_link_aqui/pub?output=csv"
# Enlace directo a tu Telegram
LINK_TELEGRAM = "https://t.me/HyGinovaciones"

# --- ESTILO MÓVIL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 10px; text-align: center;
    }
    .metric-label { font-size: 0.7rem; color: #848E9C; font-weight: bold; }
    .metric-value { font-size: 1.1rem; font-weight: bold; color: #F0B90B; }
    .login-box {
        background: #1E2329; padding: 25px; border-radius: 15px;
        border: 1px solid #F0B90B; margin-top: 30px;
    }
    .stButton>button { width: 100%; border-radius: 8px; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE AUTENTICACIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def validar_usuario(u, c):
    try:
        df_users = pd.read_csv(LINK_DB)
        check = df_users[(df_users['usuario'] == u) & (df_users['clave'].astype(str) == str(c))]
        return not check.empty
    except:
        return False

def login():
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #848E9C;'>Gestión de Licencias</p>", unsafe_allow_html=True)
    
    u = st.text_input("Usuario")
    c = st.text_input("Contraseña", type="password")
    
    if st.button("ACCEDER AL SISTEMA"):
        if validar_usuario(u, c):
            st.session_state.autenticado = True
            st.session_state.user_name = u
            st.rerun()
        else:
            st.error("❌ Licencia inválida o expirada.")
            st.markdown(f"[📩 Contactar Soporte para activar]({LINK_TELEGRAM})")
    
    st.markdown("---")
    # Botón directo a tu Telegram
    st.link_button("🚀 SOLICITAR LICENCIA", LINK_TELEGRAM)
    st.markdown("</div>", unsafe_allow_html=True)

# --- FLUJO PRINCIPAL ---
if not st.session_state.autenticado:
    login()
else:
    # --- INICIALIZACIÓN DE VARIABLES ---
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'saldo_real': 0.0, 'ganancia_acumulada': 0.0,
            'posiciones': [], 'precios_hist': [],
            'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"]),
            'ultimo_par': "", 'ultimo_modo': ""
        })

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown(f"👤 Usuario: **{st.session_state.user_name}**")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        
        st.markdown("---")
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        es_real = modo == "⚡ MODO REAL"
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
        
        if par != st.session_state.ultimo_par or modo != st.session_state.ultimo_modo:
            st.session_state.posiciones = []
            st.session_state.precios_hist = []
            st.session_state.ultimo_par = par
            st.session_state.ultimo_modo = modo

        leverage = st.slider("Apalancamiento", 1, 50, 25)
        monto = st.number_input("Inversión (USDT)", value=2.0)
        dist_grid = st.slider("Profit (%)", 0.05, 1.0, 0.1) / 100

    # --- INTERFAZ DEL BOT ---
    st.markdown("<p style='text-align: center; color: #848E9C;'>Reciba un cordial saludo de <b>H y G inovaciones</b></p>", unsafe_allow_html=True)
    bot_on = st.toggle("ENCENDER ALGORITMO")

    if bot_on:
        try:
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio = float(res['USD'])
            st.session_state.precios_hist.append(precio)
            if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)

            if not st.session_state.posiciones:
                st.session_state.posiciones.append({'precio': precio, 'id': 1})
                if not es_real: st.session_state.saldo_demo -= monto

            for i, pos in enumerate(st.session_state.posiciones):
                target = pos['precio'] * (1 + dist_grid)
                if precio >= target:
                    pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto
                    if not es_real: st.session_state.saldo_demo += (monto + pnl)
                    st.session_state.ganancia_acumulada += pnl
                    
                    new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": "WIN", "Precio": precio, "PNL": f"${pnl:.2f}"}])
                    st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                    st.session_state.posiciones.pop(i)
                    st.rerun()

            # --- PANEL MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>PRECIO</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
            with c2: 
                bal = st.session_state.saldo_real if es_real else st.session_state.saldo_demo
                st.markdown(f"<div class='metric-card'><div class='metric-label'>WALLET</div><div class='metric-value' style='color:#F0B90B;'>${bal:,.2f}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>ACUMULADO</div><div class
    
