import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 🔐 SISTEMA DE LOGIN (NO SE TOCA LA LÓGICA) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except: return False

# --- 🎨 ESTILO VISUAL ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

# --- 🛠️ CONTROL DE ESTADO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- 🚪 PANTALLA DE ACCESO (SOLO SE MUESTRA SI NO ESTÁ AUTENTICADO) ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        st.markdown("<h2 style='text-align: center;'>Acceso al Sistema</h2>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_input, p_input):
                st.session_state.autenticado = True
                st.session_state.user_name = u_input
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")

# --- 🏎️ MOTOR DEL BOT (SOLO SE MUESTRA SI YA ENTRÓ) ---
else:
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla_data': [], 'historial_pnl': [],
            'wallet': 1000.0, 'cosecha': 0.0, 'rsi_val': 52
        })

    # Header Limpio (Como en la foto 10002661
    
