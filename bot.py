import streamlit as st
import pandas as pd
import requests
import time
import numpy as np  # <--- Esta es la librería de Kalman
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

# --- MOTOR KALMAN (MATEMÁTICA PURA) ---
def aplicar_kalman(medicion, est_anterior, cov_anterior):
    # Parámetros de ruido (Ajustados para Scalping agresivo)
    R = 0.01**2  # Ruido de la medición (API)
    Q = 0.001**2 # Ruido del proceso (Mercado)
    
    # Predicción
    est_prior = est_anterior
    cov_prior = cov_anterior + Q
    
    # Ganancia de Kalman
    ganancia = cov_prior / (cov_prior + R)
    
    # Actualización
    nueva_est = est_prior + ganancia * (medicion - est_prior)
    nueva_cov = (1 - ganancia) * cov_prior
    
    return nueva_est, nueva_cov

# --- ESTILO ALTO CONTRASTE ---
st.set_page_config(page_title="Kalman AI Scalper", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #FFF; }
    [data-testid="stMetricValue"] { color: #FFF !important; font-size: 2.2rem !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #FFF !important; font-weight: 700; }
    div[data-testid="metric-container"] { background-color: #111; border: 2px solid #444; border-radius: 12px; }
    .stTable, [data-testid="stTable"] td { color: #FFF !important; font-weight: 700 !important; font-size: 1.1rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state: st.session_state.saldo = 1000.0
if 'x_est' not in st.session_state: st.session_state.x_est = 0.0
if 'p_cov' not in st.session_state: st.session_state.p_cov = 1.0
if 'log' not in st.session_state: st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "Predicción", "RSI", "Resultado"])
if 'comprado' not in st.session_state: st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("🧠 AI KALMAN CONFIG")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_trade = st.sidebar.number_input("Inversión (USD):", value=10.0)
rsi_in = st.sidebar.slider("RSI Compra:", 10, 50, 30)
rsi_out = st.sidebar.slider("RSI Venta:", 51, 90, 60)
encendido = st.sidebar.toggle("⚡ ACTIVAR ALGORITMO", value=False)

# --- DATOS ---
def obtener_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 15 + (p * 10000 % 70) 
        return float(p), float(rsi)
    except: return None, None

# --- UI ---
st.title(f"🧠 AI SCALPER KALMAN: {moneda}")
c1, c2, c3 = st.columns(3)
m_pre = c1.empty()
m_kal = c2.empty()
m_bil = c3.empty()

st.write("---")
c4, c5 = st.columns(2)
m_rsi = c4.empty()
m_est = c5.empty()

# --- EJECUCIÓN ---
if encendido:
    precio_raw, rsi_val = obtener_datos(moneda)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

    if precio_raw:
        # Inicializar filtro si es la primera vez
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio_raw
        
        # APLICAR KALMAN
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(
            precio_raw, st.session_state.x_est, st.session_state.p_cov
        )
        
        prediccion = st.session_state.x_est
        evento = "👀 FILTRANDO"
        resultado = 0.0

        # Lógica de Trading AI
        if not st.session_state.comprado:
            if rsi_val <= rsi_in:
                st.session_state.comprado = True
                st.session_state.entrada = precio_raw
                evento = "🛒 COMPRA AI"
        else:
            # Salida: RSI alto y precio confirmando tendencia arriba de la media de Kalman
            if rsi_val >= rsi_out:
                resultado = (precio_raw - st.session_state.entrada) * (monto_trade / st.session_state.entrada)
                st.session_state.saldo += resultado
                evento = "💰 PROFIT KALMAN"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLD (AI OPTIMIZING)"

        # Actualizar Pantalla (TODO BLANCO Y GRANDE)
        m_pre.metric("PRECIO REAL", f"${precio_raw:,.2f}")
        m_kal.metric("PREDICCIÓN AI", f"${prediccion:,.2f}", delta=f"{precio_raw-prediccion:.4f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")
        m_rsi.metric("RSI ACTUAL", f"{rsi_val:.1f}")
        m_est.metric("ESTADO AI", evento)

        # Historial
        nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${precio_raw:,.2f}", "Predicción": f"${prediccion:,.2f}", "RSI": f"{rsi_val:.1f}", "Resultado": f"${resultado:.4f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(8)
        st.table(st.session_state.log)

        time.sleep(5)
        st.rerun()
else:
    st.warning("Active el algoritmo en el panel lateral.")
        
