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

st.markdown("### 📈 TENDENCIA (Línea Rosa = Inteligencia Artificial)")
chart_spot = st.empty()

st.markdown("### 💰 CAJA DE GANANCIAS")
c4, c5, c6 = st.columns(3)
m_gan, m_per, m_eff = c4.empty(), c5.empty(), c6.empty()

# --- LÓGICA ---
if encendido:
    precio, rsi = traer_datos(moneda)
    if precio:
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 30:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        if len(st.session_state.precios_hist) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio', line=dict(color='#00FF00', width=3)))
            fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA Kalman', line=dict(color='#FF00FF', width=4)))
            fig.update_layout(paper_bgcolor='#4B5320', plot_bgcolor='#4B5320', font=dict(color="white"), height=300, margin=dict(l=0,r=0,t=0,b=0))
            chart_spot.plotly_chart(fig, use_container_width=True)

        evento = "VIGILANDO"
        res_t = 0.0
        
        if not st.session_state.comprado:
            if (modo == "ALCISTA (Long)" and rsi < 35) or (modo == "BAJISTA (Short)" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                st.session_state.ultima_accion = "COMPRA"
                alerta_placeholder.markdown(f'<div class="alerta-compra">🛒 ¡COMPRANDO {moneda} A ${precio:,.2f}!</div>', unsafe_allow_html=True)
                time.sleep(2) # Para que se vea el cartel
            else:
                alerta_placeholder.empty()
        else:
            res_t = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada) if modo == "ALCISTA (Long)" else (st.session_state.entrada - precio) * (monto_trade / st.session_state.entrada)
            cumple_salida = (rsi > 60 if modo == "ALCISTA (Long)" else rsi < 40)
            
            if cumple_salida:
                if not ganancia_asegurada or res_t > 0:
                    st.session_state.saldo += res_t
                    if res_t > 0: st.session_state.ganancia_total += res_t
                    else: st.session_state.perdida_total += abs(res_t)
                    st.session_state.comprado = False
                    st.session_state.ultima_accion = "VENTA"
                    alerta_placeholder.markdown(f'<div class="alerta-venta">💰 ¡VENDIENDO CON PROFIT DE ${res_t:.4f}!</div>', unsafe_allow_html=True)
                    time.sleep(2)
            else:
                alerta_placeholder.markdown(f'<div style="text-align:center; font-size:18px;">⏳ MANTENIENDO POSICIÓN (Profit actual: ${res_t:.4f})</div>', unsafe_allow_html=True)

        m_pre.metric("PRECIO", f"${precio:,.2f}")
        m_rsi.metric("RSI", f"{rsi:.1f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")
        m_gan.metric("GANADO (+)", f"${st.session_state.ganancia_total:.4f}")
        m_per.metric("PERDIDO (-)", f"${st.session_state.perdida_total:.4f}")
        m_eff.metric("ESTADO", "DENTRO" if st.session_state.comprado else "ESPERANDO")

        time.sleep(5)
        st.rerun()
else:
    st.warning("⚠️ ACTIVÁ EL BOT PARA COMENZAR")
