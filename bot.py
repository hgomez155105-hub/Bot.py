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
st.set_page_config(page_title="Ultra Scalper", layout="wide")
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

# --- SIDEBAR: CONFIGURACIÓN AGRESIVA ---
st.sidebar.header("🚀 Modo Agresivo")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_operacion = st.sidebar.number_input("Inversión por Trade (USD):", value=10.0)

st.sidebar.write("---")
# Para que sea rápido como Pionex, el rango de RSI debe ser más corto
rsi_in = st.sidebar.slider("RSI Compra (Entrar rápido):", 10, 50, 45)
rsi_out = st.sidebar.slider("RSI Venta (Salir rápido):", 51, 90, 55)

sl = st.sidebar.slider("Stop Loss %", 0.1, 2.0, 1.0)
velocidad = st.sidebar.select_slider("Frecuencia de escaneo:", options=[2, 5, 10, 15], value=5)
encendido = st.sidebar.toggle("⚡ INICIAR SCALPING", value=False)

# --- LÓGICA DE PRECIOS ---
def obtener_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url).json()['USD']
        # Simulación de RSI más volátil para generar más trades
        rsi = 20 + (p * 10000 % 60) 
        return float(p), float(rsi)
    except: return None, None

# --- UI ---
st.title(f"⚡ Ultra Scalper: {moneda}")
col1, col2, col3 = st.columns(3)
m_pre = col1.empty()
m_rsi = col2.empty()
m_bil = col3.empty()

# --- BUCLE ---
if encendido:
    precio, rsi = obtener_datos(moneda)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

    if precio:
        evento = "VIGILANDO"
        ganancia_str = "$0.00"

        # COMPRA
        if not st.session_state.comprado and rsi <= rsi_in:
            st.session_state.comprado = True
            st.session_state.entrada = precio
            st.session_state.stop = precio * (1 - (sl/100))
            evento = "🛒 COMPRA"
        
        # VENTA
        elif st.session_state.comprado:
            if rsi >= rsi_out or precio <= st.session_state.stop:
                # Calculo de ganancia
                resultado = (precio - st.session_state.entrada) * (monto_operacion / st.session_state.entrada)
                st.session_state.saldo += resultado
                ganancia_str = f"{'+' if resultado > 0 else ''}${resultado:.4f}"
                evento = "💰 VENTA PROFIT" if resultado > 0 else "📉 VENTA STOP"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLD"

        # Update visual
        m_pre.metric("PRECIO", f"${precio:,.2f}")
        m_rsi.metric("RSI ACTUAL", f"{rsi:.1f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        # Historial
        nuevo_log = {"Hora": hora, "Evento": evento, "Precio": precio, "RSI": f"{rsi:.1f}", "Ganancia": ganancia_str, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo_log]), st.session_state.log]).head(10)
        st.table(st.session_state.log)

        time.sleep(velocidad)
        st.rerun()
else:
    st.info("Bot en espera. Ajustá el RSI a un rango más corto (ej. 45/55) para más trades.")
        
