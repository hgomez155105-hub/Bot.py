import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Pro Historial", layout="wide")

# CSS: Blanco sobre Verde Militar (Sin azul)
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.2rem !important; font-weight: 800; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 2px solid #FFFFFF; border-radius: 12px; padding: 15px;
    }
    /* Estilo para la Tabla */
    .stTable td, .stTable th { color: #FFFFFF !important; background-color: #353b16 !important; border: 1px solid #FFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'log_df' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_total': 0.0, 'perdida_total': 0.0,
        'precios_hist': [], 'kalman_hist': [], 'comprado': False,
        'x_est': 0.0, 'p_cov': 1.0, 'entrada': 0.0,
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "Resultado"])
    })

def aplicar_kalman(medicion, est_anterior, cov_anterior):
    R, Q = 0.01**2, 0.001**2
    est_prior = est_anterior
    cov_prior = cov_anterior + Q
    ganancia = cov_prior / (cov_prior + R)
    nueva_est = est_prior + ganancia * (medicion - est_prior)
    nueva_cov = (1 - ganancia) * cov_prior
    return nueva_est, nueva_cov

# --- SIDEBAR ---
st.sidebar.header("🕹️ PANEL DE CONTROL")
modo = st.sidebar.radio("Estrategia:", ["ALCISTA", "BAJISTA"])
moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Monto (USD):", value=50.0)
encendido = st.sidebar.toggle("🚀 ENCENDER BOT", key="bot_activo")

# --- UI PRINCIPAL ---
st.title(f"📊 SISTEMA AI: {moneda}")

if st.session_state.bot_activo:
    try:
        # Traer precio
        url = f"https://min-api.cryptocompare.com/data/price?fsym={moneda}&tsyms=USD"
        precio = float(requests.get(url, timeout=10).json()['USD'])
        rsi = 20 + (precio * 10000 % 60)
        
        # Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        
        # UI de métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("RSI", f"{rsi:.1f}")
        c3.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        # Gráfico
        if len(st.session_state.precios_hist) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio', line=dict(color='#00FF00', width=3)))
            fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA Kalman', line=dict(color='#FF00FF', width=4)))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, font=dict(color="white"), margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

        # Lógica de Trade y Tabla de Historial
        evento = "VIGILANDO"
        res_t = 0.0
        if not st.session_state.comprado:
            if (modo == "ALCISTA" and rsi < 35) or (modo == "BAJISTA" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                evento = "🛒 COMPRA"
        else:
            res_t = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada) if modo == "ALCISTA" else (st.session_state.entrada - precio) * (monto_trade / st.session_state.entrada)
            evento = "⏳ DENTRO"

        # Actualizar la tabla de historial
        hora =
        
