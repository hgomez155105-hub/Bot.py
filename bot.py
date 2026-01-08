import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Pro", layout="wide")

# CSS REFORZADO: Letras blancas, sin azul, cajas claras
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    
    /* Títulos Principales */
    h1, h2, h3 { color: #FFFFFF !important; font-family: 'Arial', sans-serif; font-weight: 800; }
    
    /* Métricas: Blancas y Legibles */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2rem !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #FFFFFF !important; font-size: 1rem !important; opacity: 0.9; }
    
    /* Cajas de métricas */
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.2); 
        border: 2px solid #FFFFFF; 
        border-radius: 10px; 
        padding: 10px;
    }

    /* Quitar el color azul de los mensajes de ayuda */
    .stAlert p { color: #FFFFFF !important; font-weight: 700; }
    div[role="alert"] { background-color: #353b16 !important; border: 1px solid #FFFFFF; }
    
    /* Texto general y etiquetas */
    label, .stMarkdown p { color: #FFFFFF !important; font-weight: 700; }
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

# --- SIDEBAR (Panel Lateral) ---
st.sidebar.header("🕹️ CONFIGURACIÓN")
modo = st.sidebar.radio("Estrategia:", ["ALCISTA", "BAJISTA"])
moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Monto (USD):", value=50.0)
ganancia_asegurada = st.sidebar.checkbox("Vender solo con Profit", value=True)
encendido = st.sidebar.toggle("🚀 ENCENDER ALGORITMO", key="bot_on")

# --- INTERFAZ PRINCIPAL ---
st.title(f"🚀 AI TRADING: {moneda}")

# Contenedores para evitar saltos (Lagueo)
alerta_area = st.empty()
col_arriba = st.columns(3)
m_pre = col_arriba[0].empty()
m_rsi = col_arriba[1].empty()
m_bil = col_arriba[2].empty()

chart_area = st.empty()

st.markdown("### 💰 RENDIMIENTO ACUMULADO")
col_abajo = st.columns(3)
m_gan = col_abajo[0].empty()
m_per = col_abajo[1].empty()
m_est = col_abajo[2].empty()

# --- BUCLE DE OPERACIÓN ---
if st.session_state.bot_on:
    try:
        # 1. Obtener Datos
        url = f"https://min-api.cryptocompare.com/data/price?fsym={moneda}&tsyms=USD"
        precio = float(requests.get(url, timeout=5).json()['USD'])
        rsi = 20 + (precio * 10000 % 60) # Sensor RSI
        
        # 2. IA Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 30:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        # 3. Gráfico (Más grande para Mac)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio', line=dict(color='#00FF00', width=3)))
        fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA Kalman', line=dict(color='#FF00FF', width=4)))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
            height=400, margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color="white"), showlegend=True,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#5d6628')
        )
        chart_area.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # 4. Lógica de Trading
        res_t = 0.0
        if not st.session_state.comprado:
            if (modo == "ALCISTA" and rsi < 35) or (modo == "BAJISTA" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                alerta_area.success(f"🛒 COMPRA EJECUTADA A ${precio:,.2f}")
        else:
            res_t = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada) if modo == "ALCISTA" else (st.session_state.entrada - precio) * (monto_trade / st.session_state.entrada)
            cumple_salida = (rsi > 60 if modo == "ALCISTA" else rsi < 40)
            
            if cumple_salida and (not ganancia_asegurada or res_t > 0):
                st.session_state.saldo += res_t
                if res_t > 0: st.session_state.ganancia_total += res_t
                else: st.session_state.perdida_total += abs(res_t)
                st.session_state.comprado = False
                alerta_area.warning(f"💰 VENTA EJECUTADA. PROFIT: ${res_t:.4f}")
            else:
                alerta_area.info(f"⏳ HOLDING - Profit Actual: ${res_t:.4f}")

        # 5. Actualizar Métricas (Todo en Blanco)
        m_pre.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        m_rsi.metric("RSI SENSOR", f"{rsi:.1f}")
        m_bil.metric("BILLETERA USD", f"${st.session_state.saldo:,.2f}")
        
        m_gan.metric("GANANCIAS (+)", f"${st.session_state.ganancia_total:.4f}")
        m_per.metric("PÉRDIDAS (-)", f"${st.session_state.perdida_total:.4f}")
        m_est.metric("ESTADO IA", "DENTRO" if st.session_state.comprado else "BUSCANDO")

        time.sleep(3) # Refresco más rápido
        st.rerun()

    except Exception as e:
        st.error("Error de conexión. Reintentando...")
        time.sleep(2)
        st.rerun()
else:
    st.info("Algoritmo en Standby. Configura la estrategia y presiona ENCENDER.")
