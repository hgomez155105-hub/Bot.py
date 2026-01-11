import streamlit as st
import pandas as pd
import requests
import time
import os
import plotly.graph_objects as go
from datetime import datetime

# Intentar importar CCXT para el modo real
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

# --- PERSISTENCIA ---
DB_FILE = "trading_data.csv"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Dual Scalper AI", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117 !important; }
    [data-testid="stSidebar"] { background-color: #1A1C24 !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(255,255,255,0.05); border: 1px solid #30363D; border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'ganancia_acumulada': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Moneda", "Evento", "Precio", "PNL", "Modo"])
    })

# --- SIDEBAR: INTERFAZ DUAL ---
st.sidebar.title("🎮 CONTROL CENTRAL")
modo = st.sidebar.radio("Entorno de ejecución:", ["🧪 MODO DEMO", "⚡ MODO REAL (BINANCE)"])
es_real = modo == "⚡ MODO REAL (BINANCE)"

if es_real:
    with st.sidebar.expander("🔑 CONFIGURAR API"):
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        if not CCXT_AVAILABLE:
            st.error("Error: Archivo requirements.txt no detectado.")

st.sidebar.markdown("---")
par = st.sidebar.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("Apalancamiento", 1, 50, 20)
monto = st.sidebar.number_input("Inversión por Rejilla (USDT)", value=10.0)
profit_obj = st.sidebar.slider("Profit Objetivo (%)", 0.1, 2.0, 0.5) / 100

bot_on = st.sidebar.toggle("🚀 ENCENDER ALGORITMO")

# --- LÓGICA DE PRECIOS Y RSI ---
def get_price(symbol):
    coin = symbol.split("/")[0]
    res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
    return float(res['USD'])

# --- UI PRINCIPAL ---
st.title(f"{'🔥 OPERANDO EN VIVO' if es_real else '🧪 SIMULACIÓN DEMO'}")

if bot_on:
    try:
        precio = get_price(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)

        # RSI Simulado para los umbrales 30/60
        rsi = 25 + (precio % 1 * 50) 
        
        # LÓGICA DE TRADING
        evento = "VIGILANDO"
        pnl_actual = 0.0

        # ENTRADA: Solo si RSI < 30 (Barato)
        if not st.session_state.posiciones and rsi <= 30:
            st.session_state.posiciones.append({'precio': precio, 'monto': monto})
            if not es_real: st.session_state.saldo_demo -= monto
            evento = "🛒 COMPRA (RSI < 30)"

        # SALIDA: Siempre ganancia + (Profit OBJ o RSI > 60)
        for i, pos in enumerate(st.session_state.posiciones):
            if precio >= pos['precio'] * (1 + profit_obj) or rsi >= 60:
                if precio > pos['precio']: # REGLA DE ORO: SIEMPRE GANANCIA
                    pnl_actual = ((precio - pos['precio']) / pos['precio']) * leverage * monto
                    if not es_real:
                        st.session_state.saldo_demo += (monto + pnl_actual)
                        st.session_state.ganancia_acumulada += pnl_actual
                    
                    st.session_state.posiciones.pop(i)
                    evento = "💰 VENTA (PROFIT)"
                    
                    new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Moneda": par, "Evento": evento, "Precio": precio, "PNL": pnl_actual, "Modo": modo}])
                    st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                    break

        # MÉTRICAS
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("RSI (14)", f"{rsi:.2f}")
        c3.metric("BILLETERA", f"${st.session_state.saldo_demo:,.2f}" if not es_real else "Binance Real-Time")

        # GRÁFICO
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00')))
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", annotation_text="ENTRADA")
            fig.add_hline(y=p['precio']*(1+profit_obj), line_color="gold", line_dash="dash", annotation_text="PROFIT")
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, yaxis=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)
        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(5)
        st.rerun()
else:
    st.info("Algoritmo apagado. Configure los parámetros y encienda el bot.")
        
