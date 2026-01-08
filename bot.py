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

# --- ESTILO ---
st.set_page_config(page_title="AI Scalper Pro Max", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #FFF; }
    [data-testid="stMetricValue"] { color: #FFF !important; font-size: 1.8rem !important; font-weight: 800; }
    div[data-testid="metric-container"] { background-color: #111; border: 2px solid #444; border-radius: 10px; }
    .stTable td { color: #FFF !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state: st.session_state.saldo = 1000.0
if 'ganancia_total' not in st.session_state: st.session_state.ganancia_total = 0.0
if 'perdida_total' not in st.session_state: st.session_state.perdida_total = 0.0
if 'total_t' not in st.session_state: st.session_state.total_t = 0
if 'precios_hist' not in st.session_state: st.session_state.precios_hist = []
if 'kalman_hist' not in st.session_state: st.session_state.kalman_hist = []
if 'comprado' not in st.session_state: st.session_state.comprado = False
if 'x_est' not in st.session_state: st.session_state.x_est = 0.0
if 'p_cov' not in st.session_state: st.session_state.p_cov = 1.0

# --- SIDEBAR ---
st.sidebar.header("🕹️ ESTRATEGIA")
modo = st.sidebar.radio("Tendencia:", ["ALCISTA (Long)", "BAJISTA (Short)"])
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Inversión (USD):", value=10.0)
ganancia_asegurada = st.sidebar.checkbox("Vender solo con Profit", value=True)
encendido = st.sidebar.toggle("🚀 INICIAR OPERACIÓN", value=False)

# --- DATOS ---
def traer_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url).json()['USD']
        rsi = 20 + (p * 10000 % 60)
        return float(p), float(rsi)
    except: return None, None

# --- UI ---
st.title(f"📊 AI CANDLESTICK: {moneda}")
c1, c2, c3 = st.columns(3)
m_pre, m_rsi, m_bil = c1.empty(), c2.empty(), c3.empty()

# Espacio para el gráfico de velas
chart_spot = st.empty()

st.markdown("### 💰 RENDIMIENTO ACUMULADO")
c4, c5, c6 = st.columns(3)
m_gan, m_per, m_eff = c4.empty(), c5.empty(), c6.empty()

# --- BUCLE ---
if encendido:
    precio, rsi = traer_datos(moneda)
    if precio:
        # Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        # Historial para Gráfico
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 40:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        # Crear Gráfico de Velas
        df_chart = pd.DataFrame(st.session_state.precios_hist, columns=['close'])
        df_chart['open'] = df_chart['close'].shift(1).fillna(df_chart['close'])
        df_chart['high'] = df_chart[['open', 'close']].max(axis=1) + 0.1
        df_chart['low'] = df_chart[['open', 'close']].min(axis=1) - 0.1

        fig = go.Figure(data=[go.Candlestick(
            x=list(range(len(df_chart))),
            open=df_chart['open'], high=df_chart['high'],
            low=df_chart['low'], close=df_chart['close'],
            name="Precio"
        )])
        fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA Kalman', line=dict(color='#FF00FF', width=2)))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
        chart_spot.plotly_chart(fig, use_container_width=True)

        # Lógica de Trade Inteligente
        res = 0.0
        evento = "VIGILANDO"
        if not st.session_state.comprado:
            if (modo == "ALCISTA (Long)" and rsi < 35) or (modo == "BAJISTA (Short)" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                evento = "🛒 ENTRADA"
        else:
            # Cálculo de Ganancia Real
            if modo == "ALCISTA (Long)":
                res = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada)
                cumple_salida = rsi > 60
            else: # Short
                res = (st.session_state.entrada - precio) * (monto_trade / st.session_state.entrada)
                cumple_salida = rsi < 40

            if cumple_salida:
                if not ganancia_asegurada or res > 0:
                    st.session_state.saldo += res
                    st.session_state.ganancia_total += max(0, res)
                    st.session_state.perdida_total += abs(min(0, res))
                    st.session_state.total_t += 1
                    st.session_state.comprado = False
                    evento = "💰 ÉXITO"
                else:
                    evento = "⏳ HOLD (Evitando Pérdida)"

        # Métricas
        m_pre.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        m_rsi.metric("RSI", f"{rsi:.1f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")
        m_gan.metric("GANANCIAS (+)", f"${st.session_state.ganancia_total:.4f}")
        m_per.metric("PÉRDIDAS (-)", f"${st.session_state.perdida_total:.4f}")
        m_eff.metric("ESTADO", evento)

        time.sleep(5)
        st.rerun()
        
