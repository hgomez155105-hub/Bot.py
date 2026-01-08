import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- SEGURIDAD ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Acceso")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if clave == "caseros2024":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- FILTRO DE KALMAN ---
def aplicar_kalman(medicion, est_anterior, cov_anterior):
    R, Q = 0.01**2, 0.001**2
    est_prior = est_anterior
    cov_prior = cov_anterior + Q
    ganancia = cov_prior / (cov_prior + R)
    nueva_est = est_prior + ganancia * (medicion - est_prior)
    nueva_cov = (1 - ganancia) * cov_prior
    return nueva_est, nueva_cov

# --- CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="AI Scalper Pro Charts", layout="wide")
st.markdown("<style>.stApp { background-color: #000; color: #FFF; }</style>", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
if 'precios_hist' not in st.session_state: st.session_state.precios_hist = []
if 'kalman_hist' not in st.session_state: st.session_state.kalman_hist = []
if 'saldo' not in st.session_state: st.session_state.saldo = 1000.0
if 'comprado' not in st.session_state: st.session_state.comprado = False
if 'x_est' not in st.session_state: st.session_state.x_est = 0.0
if 'p_cov' not in st.session_state: st.session_state.p_cov = 1.0

# --- SIDEBAR ---
st.sidebar.header("📊 ESTRATEGIA PIONEX")
modo = st.sidebar.radio("Dirección del Mercado:", ["ALCISTA (Long)", "BAJISTA (Short)"])
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Inversión (USD):", value=10.0)
solo_ganancia = st.sidebar.checkbox("Ganancia Asegurada (No vender en pérdida)", value=True)
encendido = st.sidebar.toggle("⚡ INICIAR BOT", value=False)

# --- OBTENCIÓN DE DATOS ---
def traer_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url).json()['USD']
        rsi = 20 + (p * 10000 % 60)
        return float(p), float(rsi)
    except: return None, None

# --- UI PRINCIPAL ---
st.title(f"🚀 AI TRADING DASHBOARD: {moneda}")

col_m1, col_m2, col_m3 = st.columns(3)
m_pre = col_m1.empty()
m_rsi = col_m2.empty()
m_bil = col_m3.empty()

# CONTENEDOR DEL GRÁFICO
chart_placeholder = st.empty()

# --- LÓGICA DE EJECUCIÓN ---
if encendido:
    precio, rsi = traer_datos(moneda)
    if precio:
        # Actualizar Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        # Guardar historial para el gráfico (limitamos a 30 puntos)
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 30:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        # Crear Gráfico de Velas (Simuladas con historial)
        fig = go.Figure()
        # Línea de Precio Real
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio Real', line=dict(color='#00FF00', width=2)))
        # Línea de Tendencia Kalman (IA)
        fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='Tendencia AI (Kalman)', line=dict(color='#FF00FF', width=3, dash='dot')))
        
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20),
                          xaxis_title="Tiempo (ticks)", yaxis_title="Precio USD")
        chart_placeholder.plotly_chart(fig, use_container_width=True)

        # Lógica de Trade (Simplificada para el ejemplo)
        evento = "VIGILANDO"
        if not st.session_state.comprado:
            if (modo == "ALCISTA (Long)" and rsi < 35) or (modo == "BAJISTA (Short)" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                evento = "🛒 ENTRADA"
        else:
            res = (precio - st.session_state.entrada) if modo == "ALCISTA (Long)" else (st.session_state.entrada - precio)
            if (modo == "ALCISTA (Long)" and rsi > 60) or (modo == "BAJISTA (Short)" and rsi < 40):
                if not solo_ganancia or res > 0:
                    st.session_state.saldo += (res * (monto_trade / precio))
                    st.session_state.comprado = False
                    evento = "💰 CIERRE CON EXITO"
            else:
                evento = "⏳ HOLDING"

        # Métricas
        m_pre.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        m_rsi.metric("RSI", f"{rsi:.1f}", delta=evento)
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        time.sleep(5)
        st.rerun()
        
