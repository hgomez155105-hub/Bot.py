import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="AI Scalper Alertas", layout="wide")

# ESTILO VERDE MILITAR + ALERTAS BRILLANTES
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label, div, .stMetric label { 
        color: #FFFFFF !important; 
        font-weight: 900 !important; 
        font-family: 'Arial Black', sans-serif !important;
    }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.5rem !important; font-weight: 900 !important; }
    div[data-testid="metric-container"] { 
        background-color: #353b16; border: 3px solid #FFFFFF; border-radius: 15px; padding: 15px;
    }
    /* Estilo para las Alertas */
    .alerta-compra {
        background-color: #00FF00; color: black !important;
        padding: 20px; border-radius: 15px; text-align: center;
        font-size: 25px; font-weight: 900; border: 5px solid white;
        margin-bottom: 20px; animation: parpadeo 1s infinite;
    }
    .alerta-venta {
        background-color: #FF0000; color: white !important;
        padding: 20px; border-radius: 15px; text-align: center;
        font-size: 25px; font-weight: 900; border: 5px solid white;
        margin-bottom: 20px; animation: parpadeo 1s infinite;
    }
    @keyframes parpadeo { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
for key in ['saldo', 'ganancia_total', 'perdida_total', 'precios_hist', 'kalman_hist', 'comprado', 'x_est', 'p_cov', 'log_df', 'ultima_accion']:
    if key not in st.session_state:
        if key == 'saldo': st.session_state[key] = 1000.0
        elif key in ['precios_hist', 'kalman_hist']: st.session_state[key] = []
        elif key == 'log_df': st.session_state[key] = pd.DataFrame()
        elif key == 'p_cov': st.session_state[key] = 1.0
        elif key == 'ultima_accion': st.session_state[key] = "ESPERANDO"
        else: st.session_state[key] = 0.0

def aplicar_kalman(medicion, est_anterior, cov_anterior):
    R, Q = 0.01**2, 0.001**2
    est_prior = est_anterior
    cov_prior = cov_anterior + Q
    ganancia = cov_prior / (cov_prior + R)
    nueva_est = est_prior + ganancia * (medicion - est_prior)
    nueva_cov = (1 - ganancia) * cov_prior
    return nueva_est, nueva_cov

# --- SIDEBAR ---
st.sidebar.header("🕹️ ESTRATEGIA")
modo = st.sidebar.radio("Tendencia:", ["ALCISTA (Long)", "BAJISTA (Short)"])
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Inversión (USD):", value=50.0)
ganancia_asegurada = st.sidebar.checkbox("Vender SOLO con Profit", value=True)
encendido = st.sidebar.toggle("🚀 INICIAR OPERACIÓN", value=False)

def traer_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 20 + (p * 10000 % 60)
        return float(p), float(rsi)
    except: return None, None

# --- UI ---
st.title(f"🚀 AI BOT: {moneda} ({modo})")

# ZONA DE ALERTAS (Solo aparecen cuando hay acción)
alerta_placeholder = st.empty()

c1, c2, c3 = st.columns(3)
m_pre, m_rsi, m_bil = c1.empty(), c2.empty(), c3.empty()

st.markdown("### 📈 TENDENCIA (L
            
