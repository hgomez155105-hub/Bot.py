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

# --- ESTILO PARA CELULAR (Vertical y Compacto) ---
st.set_page_config(page_title="Scalper Mobile", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 1.4rem !important; 
        font-weight: 400 !important; 
    }
    [data-testid="stMetricLabel"] { 
        color: #AAAAAA !important; 
        font-size: 0.8rem !important; 
    }
    /* Tabla pequeña para celular */
    .stTable { font-size: 0.8rem !important; }
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 1px solid #333; 
        padding: 5px; 
        border-radius: 5px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "Ganancia", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False
    st.session_state.entrada = 0.0
    st.session_state.target_fijo = 0.0
    st.session_state.stop_fijo = 0.0

# --- SIDEBAR (Configuración rápida) ---
st.sidebar.header("⚙️ Bot Scalper")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_trade = 10.0
tp_p = st.sidebar.slider("Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Loss %", 0.1, 5.0, 2.0)
encendido = st.sidebar.toggle("🚀 ENCENDER", value=False)

# --- FUNCIÓN DE DATOS ---
def traer_datos(symbol):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        return float(res['USD'])
    except: return None

# --- PANEL PRINCIPAL ---
st.write(f"### 🤖 {moneda}")

# Fila superior compacta
c1, c2 = st.columns(2)
m_pre = c1.empty()
m_bil = c2.empty()

# Niveles
st.write("---")
c3, c4 = st.columns(2)
m_target = c3.empty()
m_stop = c4.empty()

cuadro = st.empty()

# --- LÓGICA DE TRADING ---
if encendido:
    p = traer_datos(moneda)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
    
    if p:
        # Simulamos RSI para la entrada (puedes ajustar esta lógica luego)
        rsi_sim = 30 + (p % 40) 
        evento = "VIGILANDO"
        res_dolar = "$0.00"
        
        if not st.session_state.comprado:
            target_v = p * (1 + (tp_p/100))
            stop_v = p * (1 - (sl_p/100))
            if rsi_sim < 35:
                st.session_state.comprado = True
                st.session_state.entrada = p
                st.session_state.target_fijo = target_v
                st.session_state.stop_fijo = stop_v
                evento = "🛒 COMPRA"
        else:
            target_v = st.session_state.target_fijo
            stop_v = st.session_state.stop_fijo
            
            if p >= (st.session_state.target_fijo - 0.0001):
                dif = (p - st.session_state.entrada) * (monto_trade/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"+${dif:.2f}"
                evento = "💰 PROFIT"
                st.session_state.comprado = False
            elif p <= (st.session_state.stop_fijo + 0.0001):
                dif = (p - st.session_state.entrada) * (monto_trade/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"${dif:.2f}"
                evento = "📉 STOP"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLD"

        # Actualizar Pantalla
        m_pre.metric("PRECIO", f"${p:,.2f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")
        m_target.metric("TARGET", f"${target_v:,.2f}")
        m_stop.metric("STOP", f"${stop_v:,.2f}")
        
        # Tabla mini
        nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "Ganancia": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(5)
        st.table(st.session_state.log)
        
        time.sleep(10)
        st.rerun()
else:
    cuadro.warning("Bot en espera...")
    
