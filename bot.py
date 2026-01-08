import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="AI Scalper Compact", layout="wide")

# ESTILO COMPACTO Y SIN PARPADEO
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    
    /* Achicar títulos y textos */
    h1 { font-size: 1.5rem !important; margin-bottom: 0px !important; }
    h3 { font-size: 1rem !important; margin-top: 10px !important; }
    
    /* Achicar Métricas para que entren en una fila */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 1.4rem !important; 
        font-weight: 800 !important; 
    }
    [data-testid="stMetricLabel"] { 
        font-size: 0.8rem !important; 
        color: #EEE !important;
    }
    
    /* Cajas más compactas */
    div[data-testid="metric-container"] { 
        background-color: #353b16; 
        border: 1px solid #FFF; 
        border-radius: 8px; 
        padding: 5px 10px !important;
    }

    /* Alertas más discretas pero visibles */
    .alerta-mini {
        background-color: #00FF00; color: black;
        padding: 5px; border-radius: 5px; text-align: center;
        font-size: 14px; font-weight: bold; margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_total': 0.0, 'perdida_total': 0.0,
        'precios_hist': [], 'kalman_hist': [], 'comprado': False,
        'x_est': 0.0, 'p_cov': 1.0, 'entrada': 0.0
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
st.sidebar.header("🕹️ CONFIG")
modo = st.sidebar.radio("Estrategia:", ["ALCISTA", "BAJISTA"])
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Monto USD:", value=50.0)
ganancia_asegurada = st.sidebar.checkbox("Solo Profit", value=True)
encendido = st.sidebar.toggle("🚀 ENCENDER", key="bot_on")

# --- UI FIJA (Para evitar que las cosas "salten") ---
st.title(f"🚀 {moneda} - {modo}")
alerta_spot = st.empty()
m_cols = st.columns(3)
m_pre = m_cols[0].empty()
m_rsi = m_cols[1].empty()
m_bil = m_cols[2].empty()

chart_spot = st.empty()

st.write("---")
m_cols_2 = st.columns(3)
m_gan = m_cols_2[0].empty()
m_per = m_cols_2[1].empty()
m_est = m_cols_2[2].empty()

# --- LÓGICA ---
if st.session_state.bot_on:
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={moneda}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        precio = float(res['USD'])
        rsi = 20 + (precio * 10000 % 60) # Simulado para el ejemplo
        
        # Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 25:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        # Gráfico más petiso (height=250)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', name='P', line=dict(color='#00FF00', width=2)))
        fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='K', line=dict(color='#FF00FF', width=2, dash='dot')))
        fig.update_layout(paper_bgcolor='#4B5320', plot_bgcolor='#4B5320', height=220, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        chart_spot.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Lógica de Trade
        res_t = 0.0
        if not st.session_state.comprado:
            if (modo == "ALCISTA" and rsi < 35) or (modo == "BAJISTA" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                alerta_spot.markdown('<div class="alerta-mini">🛒 COMPRADO</div>', unsafe_allow_html=True)
        else:
            res_t = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada) if modo == "ALCISTA" else (st.session_state.entrada - precio) * (monto_trade / st.session_state.entrada)
            cumple_salida = (rsi > 60 if modo == "ALCISTA" else rsi < 40)
            
            if cumple_salida and (not ganancia_asegurada or res_t > 0):
                st.session_state.saldo += res_t
                if res_t > 0: st.session_state.ganancia_total += res_t
                else: st.session_state.perdida_total += abs(res_t)
                st.session_state.comprado = False
                alerta_spot.markdown(f'<div class="alerta-mini" style="background:red; color:white;">💰 VEND
            
