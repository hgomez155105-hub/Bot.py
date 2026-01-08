import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- SEGURIDAD ---
PASSWORD = "caseros2024"
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if clave == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# --- ESTILO ---
st.set_page_config(page_title="Ultra Scalper Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    [data-testid="stMetricValue"] { color: #00FF00 !important; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #222; border-radius: 10px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("🚀 Configuración")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_operacion = st.sidebar.number_input("Monto por Trade (USD):", value=10.0)

rsi_in = st.sidebar.slider("RSI Compra:", 10, 50, 30)
rsi_out = st.sidebar.slider("RSI Venta:", 51, 90, 60)
sl = st.sidebar.slider("Stop Loss % (Seguridad)", 0.1, 5.0, 2.0)
velocidad = st.sidebar.select_slider("Velocidad (seg):", options=[2, 5, 10, 30], value=5)
encendido = st.sidebar.toggle("⚡ INICIAR BOT", value=False)

# --- DATOS ---
def obtener_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 15 + (p * 10000 % 70) # Simulación más reactiva
        return float(p), float(rsi)
    except: return None, None

# --- UI ---
st.title(f"⚡ Scalper: {moneda}")
col1, col2, col3 = st.columns(3)
m_pre = col1.empty()
m_rsi = col2.empty()
m_bil = col3.empty()

# --- LÓGICA ---
if encendido:
    precio, rsi = obtener_datos(moneda)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

    if precio:
        evento = "VIGILANDO"
        ganancia_str = "$0.00"

        # 1. COMPRA
        if not st.session_state.comprado:
            if rsi <= rsi_in:
                st.session_state.comprado = True
                st.session_state.entrada = precio
                st.session_state.stop = precio * (1 - (sl/100))
                evento = "🛒 COMPRA"
        
        # 2. VENTA
        else:
            # PRIORIDAD: Si toca el RSI de venta, es PROFIT
            if rsi >= rsi_out:
                resultado = (precio - st.session_state.entrada) * (monto_operacion / st.session_state.entrada)
                st.session_state.saldo += resultado
                ganancia_str = f"+${resultado:.4f}"
                evento = "💰 VENTA PROFIT"
                st.session_state.comprado = False
            
            # SEGUNDA OPCIÓN: Si toca el precio de Stop Loss
            elif precio <= st.session_state.stop:
                resultado = (precio - st.session_state.entrada) * (monto_operacion / st.session_state.entrada)
                st.session_state.saldo += resultado
                ganancia_str = f"${resultado:.4f}"
                evento = "📉 VENTA STOP"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLD (Esperando RSI)"

        # Visuales
        m_pre.metric("PRECIO", f"${precio:,.2f}")
        m_rsi.metric("RSI ACTUAL", f"{rsi:.1f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        nuevo_log = {"Hora": hora, "Evento": evento, "Precio": precio, "RSI": f"{rsi:.1f}", "Ganancia": ganancia_str, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo_log]), st.session_state.log]).head(10)
        st.table(st.session_state.log)

        time.sleep(velocidad)
        st.rerun()
                
