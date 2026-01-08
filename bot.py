import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="AI Scalper Verde Militar", layout="wide")

# ESTILO VERDE MILITAR Y LETRAS BLANCAS
st.markdown("""
    <style>
    /* Fondo Verde Militar para toda la app */
    .stApp { 
        background-color: #4B5320 !important; 
        color: #FFFFFF !important; 
    }
    
    /* Sidebar Verde Militar más oscuro */
    section[data-testid="stSidebar"] { 
        background-color: #353b16 !important; 
    }

    /* Números y letras de métricas */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 2.2rem !important; 
        font-weight: 800 !important; 
    }
    
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
        font-weight: 800 !important;
    }
    
    /* Cajas de métricas en verde oscuro */
    div[data-testid="metric-container"] { 
        background-color: #353b16; 
        border: 2px solid #FFFFFF; 
        border-radius: 12px; 
        padding: 10px;
    }

    /* Tabla con fondo verde y letras blancas */
    .stTable, [data-testid="stTable"] td, [data-testid="stTable"] th { 
        background-color: #4B5320 !important;
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
        font-weight: 800 !important; 
        border-bottom: 1px solid #FFFFFF !important;
    }
    
    /* Títulos y textos generales */
    h1, h2, h3, p, span, label { 
        color: #FFFFFF !important; 
        font-weight: 800 !important; 
    }

    /* Ajuste para inputs y botones */
    .stButton>button { background-color: #353b16; color: white; border: 1px solid white; }
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
