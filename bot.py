import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="AI Scalper Militar Pro", layout="wide")

# ESTILO VERDE MILITAR + LETRAS BLANCAS BRILLANTES
st.markdown("""
    <style>
    /* Fondo Verde Militar */
    .stApp { background-color: #4B5320 !important; }
    
    /* Forzar color blanco en TODO el texto */
    h1, h2, h3, p, span, label, div, .stMetric label { 
        color: #FFFFFF !important; 
        font-weight: 900 !important; 
        font-family: 'Arial Black', sans-serif !important;
    }
    
    /* Métricas: Números grandes y blancos */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 2.5rem !important; 
        font-weight: 900 !important; 
    }
    
    /* Cajas de las métricas */
    div[data-testid="metric-container"] { 
        background-color: #353b16; 
        border: 3px solid #FFFFFF; 
        border-radius: 15px; 
        padding: 15px;
    }

    /* Tabla: Letras blancas y fondo verde */
    .stTable td, .stTable th { 
        color: #FFFFFF !important; 
        font-weight: 800 !important; 
        background-color: #353b16 !important;
        border: 1px solid #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
for key in ['saldo', 'ganancia_total', 'perdida_total', 'total_t', 'precios_hist', 'kalman_hist', 'comprado', 'x_est', 'p_cov', 'log_df']:
    if key not in st.session_state:
        if key == 'saldo': st.session_state[key] = 1000.0
        elif key in ['precios_hist', 'kalman_hist']: st.session_state[key] = []
        elif key == 'log_df': st.session_state[key] = pd.DataFrame()
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

# --- FUNCIÓN DE DATOS ---
def traer_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 20 + (p * 10000 % 60)
        return float(p), float(rsi)
    except: return None, None

# --- UI PRINCIPAL ---
st.title(f"🚀 AI TRADING: {moneda} ({modo})")

# Crear contenedores vacíos para que no desaparezcan
c1, c2, c3 = st.columns(3)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()

st.markdown("### 📈 GRÁFICO DE TENDENCIA")
chart_spot = st.empty()

st.markdown("### 💰 RENDIMIENTO")
c4, c5, c6 = st.columns(3)
m_gan = c4.empty()
m_per = c5.empty()
m_eff = c6.empty()

# --- LÓGICA ---
if encendido:
    precio, rsi = traer_datos(moneda)
    if precio:
        # Inicializar Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        # Guardar Historial
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 30:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        # Mostrar Gráfico
        if len(st.session_state.precios_hist) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio', line=dict(color='#00FF00', width=3)))
            fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA Kalman', line=dict(color='#FF00FF', width=4)))
            fig.update_layout(paper_bgcolor='#4B5320', plot_bgcolor='#4B5320', font=dict(color="white"), height=300, margin=dict(l=0,r=0,t=0,b=0))
            chart_spot.plotly_chart(fig, use_container_width=True)

        # Lógica de Trade
        evento = "VIGILANDO"
        res_t = 0.0
        if not st.session_state.comprado:
            if (modo == "ALCISTA (Long)" and rsi < 35) or (modo == "BAJISTA (Short)" and rsi > 65):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                evento = "🛒 ENTRADA"
        else:
            res_t = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada) if modo == "ALCISTA (Long)" else (st.session_state.entrada - precio) * (monto_trade / st.session_state.entrada)
            cumple_salida = (rsi > 60 if modo == "ALCISTA (Long)" else rsi < 40)
            
            if cumple_salida:
                if not ganancia_asegurada or res_t > 0:
                    st.session_state.saldo += res_t
                    if res_t > 0: st.session_state.ganancia_total += res_t
                    else: st.session_state.perdida_total += abs(res_t)
                    st.session_state.comprado = False
                    evento = "💰 ÉXITO"
                else:
                    evento = "⏳ HOLD (Profit)"

        # Llenar Métricas
        m_pre.metric("PRECIO", f"${precio:,.2f}")
        m_rsi.metric("RSI", f"{rsi:.1f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")
        m_gan.metric("GANADO (+)", f"${st.session_state.ganancia_total:.4f}")
        m_per.metric("PERDIDO (-)", f"${st.session_state.perdida_total:.4f}")
        m_eff.metric("ESTADO", evento)

        # Tabla de Historial
        hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
        nuevo = {"Hora": hora, "Evento": evento, "Precio": precio, "Resultado": res_t}
        st.session_state.log_df = pd.concat([pd.DataFrame([nuevo]), st.session_state.log_df]).head(5)
        st.table(st.session_state.log_df)

        time.sleep(5)
        st.rerun()
else:
    st.warning("⚠️ ACTIVÁ EL BOT EN EL PANEL LATERAL PARA VER EL GRÁFICO")
        
