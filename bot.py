import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 🔐 ACCESO (INTOCABLE) ---
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

# --- 🎨 ESTILO PREDADOR ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- 🚪 LOGIN ---
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

# --- 🚀 MOTOR PREDADOR (REPARADO) ---
else:
    # Inicialización forzada de variables
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [0.0], 'malla_data': [], 'historial_pnl': [],
            'wallet': 1000.0, 'cosecha': 0.20, 'ultimo_par': ""
        })

    # PANEL LATERAL
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=80)
        monedas = ["SOL/USDT", "BTC/USDT", "ETH/USDT", "ETC/USDT", "BNB/USDT", "FET/USDT", "PEPE/USDT", "DOGE/USDT", "LINK
        
