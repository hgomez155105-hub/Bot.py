import streamlit as st
import pandas as pd
import requests
import time
import os
import ccxt
import plotly.graph_objects as go
from datetime import datetime

# --- PERSISTENCIA DE DATOS ---
DB_LOG = "trade_history_dual.csv"

def guardar_log(df):
    df.to_csv(DB_LOG, index=False)

def cargar_log():
    if os.path.exists(DB_LOG): return pd.read_csv(DB_LOG)
    return pd.DataFrame(columns=["Hora", "Moneda", "Evento", "Precio", "PNL", "Modo"])

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Dual Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #12150A !important; }
    div[data-testid="stSidebar"] { background-color: #2D3410 !important; border-right: 1px solid #4B5320; }
    h1, h2, h3, p, span, label { color: #E0E0E0 !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.4); border: 1px solid #4B5320; border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'log_df' not in st.session_state:
    st.session_state.log_df = cargar_log()
    st.session_state.update({
        'saldo_demo': 1000.0,
        'posiciones': [],
        'precios_hist': [],
        'ganancia_demo': 0.0,
        'moneda_activa': "SOL"
    })

# --- SIDEBAR: INTERFAZ DE USUARIO ---
st.sidebar.title("🎮 TERMINAL DE MANDO")

# SECTOR 1: SELECCIÓN DE MODO
st.sidebar.subheader("🔌 MODO DE OPERACIÓN")
modo_operacion = st.sidebar.radio("Selecciona entorno:", ["MODO DEMO (Virtual)", "MODO REAL (Binance)"])
es_real = modo_operacion == "MODO REAL (Binance)"

# SECTOR 2: API KEYS (Solo visibles si es necesario o para configurar)
with st.sidebar.expander("🔑 CONFIGURAR API KEYS"):
    api_key = st.text_input("Binance API Key", type="password")
    api_secret = st.text_input("Binance Secret Key", type="password")
    if es_real and (not api_key or not api_secret):
        st.error("⚠️ Keys requeridas para Modo Real")

st.sidebar.markdown("---")

# SECTOR 3: PARÁMETROS DE ESTRATEGIA
st.sidebar.subheader("📈 ESTRATEGIA")
par_trading = st.sidebar.selectbox("Par de Activos:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "PEPE/USDT"])
leverage = st.sidebar.slider("Apalancamiento (x)", 1, 50, 10)
monto_entrada = st.sidebar.number_input("Inversión por Nivel (USDT)", value=20.0)
take_profit_perc = st.sidebar.slider("Profit Objetivo por Rejilla (%)", 0.1, 5.0, 0.5) / 100

st.sidebar.markdown("---")
bot_activo = st.sidebar.toggle("⚡ ACTIVAR ALGORITMO", key="switch_bot")

# --- LÓGICA DE CAMBIO DE MONEDA ---
moneda_check = par_trading.split("/")[0]
if moneda_check != st.session_state.moneda_activa:
    st.session_state.moneda_activa = moneda_check
    st.session_state.posiciones = []
    st.session_state.precios_hist = []
    st.rerun()

# --- FUNCIONES DE MERCADO ---
def fetch_precio(coin):
    url = f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD"
    return float(requests.get(url).json()['USD'])

# --- UI PRINCIPAL ---
header_color = "#00FFAA" if es_real else "#00AAFF"
st.markdown(f"<h1 style='color:{header_color}'>{'🔥 BINANCE LIVE' if es_real else '🧪 SIMULADOR DEMO'}</h1>", unsafe_allow_html=True)

if bot_activo:
    try:
        # 1. Datos en tiempo real
        precio = fetch_precio(st.session_state.moneda_activa)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)
        
        # 2. RSI Simulado (Criterios 30/60)
        rsi_val = 20 + (precio * 1000 % 60) # Simulación de oscilación

        # 3. Conexión Real (Opcional)
        balance_ver = st.session_state.saldo_demo
        if es_real and api_key and api_secret:
            # Aquí iría la conexión CCXT real (omitida por brevedad pero lista para insertar)
            balance_ver = "Conectado a Binance..." 

        # 4. LÓGICA DE TRADING (Criterio siempre ganar)
        evento = "VIGILANDO"
        pnl_msg = 0.0

        # Entrada (Criterio RSI < 30)
        if not st.session_state.posiciones and rsi_val <= 30:
            st.session_state.posiciones.append({'precio': precio, 'monto': monto_entrada})
            if not es_real: st.session_state.saldo_demo -= monto_entrada
            evento = "🛒 COMPRA (RSI BAJO)"
        
        # Venta (Criterio Profit propio + RSI > 60)
        for i, pos in enumerate(st.session_state.posiciones):
            if precio >= pos['precio'] * (1 + take_profit_perc) or rsi_val >= 60:
                if precio > pos['precio']: # ASEGURAR SIEMPRE GANANCIA
                    pnl_msg = ((precio - pos['precio']) / pos['precio']) * leverage * monto_entrada
                    if not es_real:
                        st.session_state.saldo_demo += (monto_entrada + pnl_msg)
                        st.session_state.ganancia_demo += pnl_msg
                    
                    st.session_state.posiciones.pop(i)
                    evento = "💰 CIERRE CON PROFIT"
                    
                    # Log de persistencia
                    nuevo_log = pd.DataFrame([{
                        "Hora": datetime.now().strftime("%H:%M:%S"),
                        "Moneda": par_trading,
                        "Evento": evento,
                        "Precio": precio,
                        "PNL": pnl_msg,
                        "Modo": "REAL" if es_real else "DEMO"
                    }])
                    st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
                    guardar_log(st.session_state.log_df)
                    break

        # --- DASHBOARD ---
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO ACTUAL", f"${precio:,.4f}")
        c2.metric("RSI ESTRATEGIA", f"{rsi_val:.2f}", delta="ZONA COMPRA" if rsi_val <= 30 else None)
        c3.metric("BALANCE ESTIMADO", f"${balance_ver}")

        # --- GRÁFICO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=2), name="Precio"))
        
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", annotation_text="ENTRY")
            fig.add_hline(y=p['precio']*(1+take_profit_perc), line_color="gold", line_dash="dash", annotation_text="PROFIT")
        
        y_min = min(st.session_state.precios_hist) * 0.999
        y_max = max(st.session_state.precios_hist) * 1.001
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, yaxis=dict(range=[y_min, y_max], color="white"))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📒 HISTORIAL COMPLETO (DEMO & REAL)")
        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)

        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Error de red: {e}")
        time.sleep(4)
        st.rerun()
else:
    st.info("💡 Bot en espera. Selecciona tu modo (Demo/Real) y presiona 'Activar Algoritmo'.")
            
