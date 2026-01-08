import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="AI Scalper Ultra Bright", layout="wide")

# ESTILO DE ALTO CONTRASTE (BLANCO PURO TOTAL)
st.markdown("""
    <style>
    /* Fondo negro */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Números de métricas */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 2.2rem !important; 
        font-weight: 800 !important; 
    }
    
    /* Etiquetas de métricas (Letras de arriba) */
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
        font-weight: 800 !important;
        text-transform: uppercase;
    }
    
    /* Caja de métricas */
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 2px solid #555; 
        border-radius: 12px; 
    }

    /* TODA LA TABLA: Letras blancas brillantes */
    .stTable, [data-testid="stTable"] td, [data-testid="stTable"] th { 
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
        font-weight: 800 !important; 
        border-bottom: 1px solid #444 !important;
        opacity: 1 !important;
    }
    
    /* Títulos y Subtítulos */
    h1, h2, h3, p, span { 
        color: #FFFFFF !important; 
        font-weight: 800 !important; 
    }

    /* Sidebar letras */
    section[data-testid="stSidebar"] { background-color: #050505 !important; }
    .stSlider label, .stSelectbox label, .stNumberInput label, .stRadio label { 
        color: #FFFFFF !important; 
        font-weight: 700 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
for key in ['saldo', 'ganancia_total', 'perdida_total', 'total_t', 'precios_hist', 'kalman_hist', 'comprado', 'x_est', 'p_cov']:
    if key not in st.session_state:
        if key == 'saldo': st.session_state[key] = 1000.0
        elif key in ['precios_hist', 'kalman_hist']: st.session_state[key] = []
        elif key == 'p_cov': st.session_state[key] = 1.0
        else: st.session_state[key] = 0.0

# --- FILTRO KALMAN ---
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

# --- DATOS ---
def traer_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 20 + (p * 10000 % 60)
        return float(p), float(rsi)
    except: return None, None

# --- UI ---
st.title(f"📊 AI TRADING: {moneda}")
c1, c2, c3 = st.columns(3)
m_pre, m_rsi, m_bil = c1.empty(), c2.empty(), c3.empty()

st.markdown("### 📈 GRÁFICO DE TENDENCIA (IA)")
chart_spot = st.empty()

st.markdown("### 💰 CAJA DE GANANCIAS")
c4, c5, c6 = st.columns(3)
m_gan, m_per, m_eff = c4.empty(), c5.empty(), c6.empty()

# --- BUCLE ---
if encendido:
    precio, rsi = traer_datos(moneda)
    
