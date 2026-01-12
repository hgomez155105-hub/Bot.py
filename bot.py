import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="centered")

# --- ENLACE DE TU BASE DE DATOS ---
LINK_DB = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"
LINK_TELEGRAM = "https://t.me/HyGinovaciones"

# --- COLOCA TUS API KEYS MANUALMENTE AQUÍ ---
API_KEY = "TU_API_KEY_AQUI"
API_SECRET = "TU_SECRET_KEY_AQUI"

# --- ESTILO ---
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
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def validar_usuario(u, c):
    try:
        df_users = pd.read_csv(LINK_DB)
        df_users.columns = df_users.columns.str.strip().str.lower()
        u_ingresado, c_ingresado = str(u).strip(), str(c).strip()
        check = df_users[(df_users['usuario'].astype(str).str.strip() == u_ingresado) & 
                         (df_users['clave'].astype(str).str.strip() == c_ingresado)]
        return not check.empty
    except: return False

if not st.session_state.autenticado:
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
    u = st.text_input("Usuario")
    c = st.text_input("Contraseña", type="password")
    if st.button("ACCEDER AL SISTEMA", use_container_width=True):
        if validar_usuario(u, c):
            st.session_state.autenticado = True
            st.session_state.user_name = u
            st.rerun()
        else: st.error("❌ Licencia inválida.")
    st.link_button("🚀 SOLICITAR LICENCIA", LINK_TELEGRAM, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({'saldo_demo': 10
