import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Pro Max", layout="wide")

# CSS: Estética Mac / Verde Militar
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 1px solid #FFFFFF; border-radius: 10px; padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADO ---
if 'moneda_actual' not in st.session_state:
    st.session_state.moneda_actual = "BTC"

# Función para resetear si cambias de moneda
def reset_memoria():
    st.session_state.precios_hist = []
    st.session_state.kalman_hist = []
    st.session_state.comprado = False
    st.session_state.x_est = 0.0
    st.session_state.p_cov = 1.0

if 'log_df' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_acumulada': 0.0, 
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
nueva_moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "ADA", "XRP"])

# Si el usuario cambia la moneda, reseteamos gráfico y memoria
if nueva_moneda != st.session_state.moneda_actual:
    st.session_state.moneda_actual = nueva_moneda
    reset_memoria()
    st.rerun()

monto_trade = st.sidebar.number_input("Inversión (USD):", value=100.0)

st.sidebar.subheader("🎯 SENSORES")
tp_perc = st.sidebar.slider("Toma de ganancias (%)", 0.1, 5.0, 0.5) / 100
sl_perc = st.sidebar.slider("Stop Loss (%)", 0.1, 5.0, 0.5) / 100
encendido = st.sidebar.toggle("🚀 BOT ENCENDEDOR", key="bot_activo")

# --- UI PRINCIPAL ---
st.title(f"📊 BOT de IA: {st.session_state.moneda_actual}")

if st.session_state.bot_activo:
    try:
        # 1. Obtener precio fresco
        url = f"https://min-api.cryptocompare.com/data/price?fsym={st.session_state.moneda_actual}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        precio = float(res['USD'])
        
        # 2. IA Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        st.session_state.precios_hist.append(precio)
        st.session_state.kalman_hist.append(st.session_state.x_est)
        if len(st.session_state.precios_hist) > 50:
            st.session_state.precios_hist.pop(0)
            st.session_state.kalman_hist.pop(0)

        # 3. Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        c2.metric("GANANCIA ACUM.", f"${st.session_state.ganancia_acumulada:.2f}")
        c3.metric("BILLETERA (CASH)", f"${st.session_state.saldo:,.2f}")

        # 4. Gráfico dinámico (zoom automático)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio', line=dict(color='#00FF00')))
        fig.add_trace(go.Scatter(y=st.session_state.kalman_hist, mode='lines', name='IA', line=dict(color='#FF00FF', dash='dot')))
        
        if st.session_state.comprado:
            fig.add_hline(y=st.session_state.entrada, line_color="white", annotation_text="COMPRA")
            fig.add_hline(y=st.session_state.precio_objetivo, line_color="gold", annotation_text="META")
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
            height=350, margin=dict(l=0,r=0,t=0,b=0), font=dict(color="white"),
            yaxis=dict(autorange=True, fixedrange=False) # Esto arregla el gráfico plano
        )
        st.plotly_chart(fig, use_container_width=True)

        # 5. Lógica de Trading y Billetera
        evento = "VIGILANDO"
        res_t = 0.0
        
        if not st.session_state.comprado:
            # Comprar si el precio cruza la IA (ejemplo de señal)
            if precio < st.session_state.x_est * 0.999: 
                st.session_state.comprado = True
                st.session_state.entrada = precio
                st.session_state.precio_objetivo = precio * (1 + tp_perc)
                st.session_state.saldo -= monto_trade # DESCUENTO REAL
                evento = "🛒 COMPRA"
        else:
            diff = (precio - st.session_state.entrada)
            perc = diff / st.session_state.entrada
            if perc >= tp_perc or perc <= -sl_perc:
                res_t = diff * (monto_trade / st.session_state.entrada)
                st.session_state.saldo += (monto_trade + res_t) # DEVOLUCIÓN + RESULTADO
                st.session_state.ganancia_acumulada += res_t
                if res_t > 0: st.session_state.trades_ganados += 1
                else: st.session_state.trades_perdidos += 1
                st.session_state.comprado = False
                evento = "💰 VENTA"
            else:
                evento = "🎯 DENTRO"

        # 6. Tabla e Historial
        hora = datetime.now().strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "Resultado": f"${res_t:.4f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
        
        st.markdown("### 🏆 EFECTIVIDAD")
        col_e1, col_e2 = st.columns(2)
        col_e1.write(f"✅ Ganados: {st.session_state.trades_ganados} | ❌ Perdidos: {st.session_state.trades_perdidos}")
        st.dataframe(st.session_state.log_df, use_container_width=True, height=200)

        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.info("Sincronizando con el exchange...")
        time.sleep(2)
        st.rerun()
else:
    st.warning("⚠️ ACTIVÁ EL BOT PARA COMENZAR")
        
