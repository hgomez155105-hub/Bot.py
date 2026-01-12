import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper - H y G", layout="wide")

# --- LÓGICA DE CÁLCULO RSI ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- ESTILO VISUAL BINANCE DARK ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 15px; text-align: center;
    }
    .metric-label { font-size: 0.8rem; color: #848E9C; }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #F0B90B; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    # Pantalla de acceso (puedes volver a poner tu lógica de Google Sheets aquí)
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
    if st.button("INGRESAR AL SISTEMA", use_container_width=True):
        st.session_state.autenticado = True
        st.rerun()
else:
    # Inicialización de variables de trading
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_pendientes': [], 'ultimo_par': ""
        })

    # --- BARRA LATERAL: TODOS LOS CONTROLES MANUALES ---
    with st.sidebar:
        st.title("🛡️ Panel de Usuario")
        
        # 1. ENTORNO MANUAL
        modo = st.radio("MODO DE TRADING:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        es_real = modo == "⚡ MODO REAL"
        
        st.markdown("---")
        # 2. APIS MANUALES
        st.subheader("🔑 Credenciales API")
        user_api_key = st.text_input("Binance API Key", type="password", placeholder="Pega tu API Key")
        user_api_secret = st.text_input("Binance Secret Key", type="password", placeholder="Pega tu Secret Key")
        
        st.markdown("---")
        # 3. RSI MANUAL (Resguardo)
        st.subheader("📉 Resguardo RSI")
        rsi_manual = st.slider("Cerrar por RSI alto en:", 50, 95, 75, help="Si el RSI toca este nivel y estás en ganancia, el bot cierra para asegurar.")
        
        st.markdown("---")
        # 4. MONEDA Y APALANCAMIENTO MANUAL
        st.subheader("📊
        
