import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Pro Max", layout="wide")

# CSS: Blanco sobre Verde Militar
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; font-weight: 800; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 1px solid #FFFFFF; border-radius: 10px; padding: 10px;
    }
    /* Estilo para el dataframe (historial) */
    .stDataFrame { background-color: #353b16 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA ---
if 'log_df' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_total': 0.0, 'perdida_total': 0.0,
        'trades_ganados': 0, 'trades_perdidos': 0,
        'precios_hist': [], 'kalman_hist': [], 'comprado': False,
        'x_est': 0.0, 'p_cov': 1.0, 'entrada': 0.0, 'precio_objetivo': 0.0,
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
st.sidebar.header("🕹️ ESTRATEGIA")
modo = st.sidebar.radio("Tendencia:", ["ALCISTA", "BAJISTA"])
moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "ADA", "XRP"])
monto_trade = st.sidebar.number_input("Inversión (USD):", value=100.0)

st.sidebar.subheader("🎯 SENSORES")
rsi_compra = st.sidebar.slider("RSI Compra:", 10, 40, 30)
rsi_venta = st.sidebar.slider("RSI Venta:", 60, 90, 70)
tp_perc = st.sidebar.slider("Take Profit (%)", 0.1, 5.0, 1.0) / 100
sl_perc = st.sidebar.slider("Stop Loss (%)", 0.1, 5.0, 1.0) / 100

ganancia_asegurada = st.sidebar.toggle("Cerrar SOLO con Ganancia", value=True)
encendido = st.sidebar.toggle("🚀 ENCENDER BOT", key="bot_activo")

# --- UI PRINCIPAL ---
st.title(f"📊 AI BOT: {moneda} ({modo})")

if st.session_state.bot_activo:
    try:
        # Traer precio real
        url = f"https://min-api.cryptocompare.com/data/price?fsym={moneda}&tsyms=USD"
        precio = float(requests.get(url, timeout=10).json()['USD'])
        rsi = 20 + (precio * 10000 % 60) # Sensor RSI
        
        # Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        
        # Métricas Principales
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        c2.metric("RSI", f"{rsi:.1f}")
        c3.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        # Gráfico con líneas de meta
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', name='Precio', line=dict(color='#00FF00', width=2)))
        fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA Kalman', line=dict(color='#FF00FF', width=2, dash='dot')))
        
        if st.session_state.comprado:
            fig.add_hline(y=st.session_state.entrada, line_dash="dash", line_color="white", annotation_text="COMPRA")
            fig.add_hline(y=st.session_state.precio_objetivo, line_dash="dash", line_color="gold", annotation_text="META TP")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, font=dict(color="white"), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # --- ESTADÍSTICAS DE EFECTIVIDAD ---
        st.markdown("### 🏆 RENDIMIENTO Y EFECTIVIDAD")
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("GANADOS", f"{st.session_state.trades_ganados} ✅")
        e2.metric("PERDIDOS", f"{st.session_state.trades_perdidos} ❌")
        
        total_trades = st.session_state.trades_ganados + st.session_state.trades_perdidos
        efectividad = (st.session_state.trades_ganados / total_trades * 100) if total_trades > 0 else 0
        e3.metric("EFECTIVIDAD", f"{efectividad:.1f}%")
        e4.metric("NETO USD", f"${(st.session_state.ganancia_total - st.session_state.perdida_total):.2f}")

        # Lógica de Trading
        evento = "VIGILANDO"
        res_t = 0.0
        
        if not st.session_state.comprado:
            if (modo == "ALCISTA" and rsi <= rsi_compra) or (modo == "BAJISTA" and rsi >= rsi_venta):
                st.session_state.comprado = True
                st.session_state.entrada = precio
                st.session_state.precio_objetivo = precio * (1 + tp_perc) if modo == "ALCISTA" else precio * (1 - tp_perc)
                evento = "🛒 COMPRA"
        else:
            diff = (precio - st.session_state.entrada) if modo == "ALCISTA" else (st.session_state.entrada - precio)
            perc_actual = diff / st.session_state.entrada
            res_t = diff * (monto_trade / st.session_state.entrada)
            
            if perc_actual >= tp_perc or perc_actual <= -sl_perc or (rsi >= rsi_venta if modo == "ALCISTA" else rsi <= rsi_compra):
                if not ganancia_asegurada or res_t > 0 or perc_actual <= -sl_perc:
                    st.session_state.saldo += res_t
                    if res_t > 0: 
                        st.session_state.ganancia_total += res_t
                        st.session_state.trades_ganados += 1
                    else: 
                        st.session_state.perdida_total += abs(res_t)
                        st.session_state.trades_perdidos += 1
                    st.session_state.comprado = False
                    evento = "💰 VENTA"
            else:
                evento = "🎯 DENTRO"

        # Historial Permanente
        hora = (datetime.now()).strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "Resultado": f"${res_t:.4f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)

        st.markdown("### 📋 HISTORIAL COMPLETO (Scroll para ver atrás)")
        st.dataframe(st.session_state.log_df, use_container_width=True, height=300)

        time.sleep(4)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(2)
        st.rerun()
else:
    st.info("Bot en espera. Configurá los parámetros y dale a 'ENCENDER'.")
