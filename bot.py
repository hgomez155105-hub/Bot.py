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
    if st.button("Entrar"):
        if clave == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# --- ESTILO ULTRA RESALTADO (TABLA BLANCA) ---
st.set_page_config(page_title="Scalper Bot", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    
    /* Números de arriba (Métricas) */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 3rem !important; 
        font-weight: 800 !important; 
    }
    
    /* Títulos de las Métricas */
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-size: 1.3rem !important; 
        font-weight: 700 !important;
    }

    /* --- TABLA DE ABAJO TOTALMENTE BLANCA Y RESALTADA --- */
    .stTable, [data-testid="stTable"] {
        background-color: #111 !important;
        color: #FFFFFF !important;
    }
    
    /* Forzar que cada celda de la tabla sea blanca y gruesa */
    .stTable td, .stTable th, [data-testid="stTable"] td {
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        border-bottom: 1px solid #444 !important;
        padding: 12px !important;
    }

    /* Resaltar el contenedor de las métricas */
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 3px solid #555; 
        padding: 20px; 
        border-radius: 15px; 
    }
    </style>
    """, unsafe_allow_html=True)

if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
    st.session_state.comprado = False
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])

# --- CONEXIÓN ESTABLE ---
def traer_datos_seguros():
    try:
        url = "https://min-api.cryptocompare.com/data/price?fsym=SOL&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        p = float(res['USD'])
        rsi_sim = 30 + (p % 40)
        return p, rsi_sim
    except:
        return None, None

# --- PANEL PRINCIPAL ---
st.title("🤖 Centro de Mando Pro")
c1, c2, c3, c4 = st.columns(4)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()
m_est = c4.empty()

st.sidebar.header("⚙️ Ajustes")
tp = st.sidebar.slider("Profit %", 0.1, 2.0, 0.8)
sl = st.sidebar.slider("Loss %", 0.1, 5.0, 2.0)
if st.sidebar.button("🔒 Salir"):
    st.session_state.auth = False
    st.rerun()

# --- LOOP ---
st.write("---")
cuadro = st.empty()
if st.sidebar.button("🚀 INICIAR AHORA"):
    cuadro.info("🛰️ Conectando...")
    while True:
        p, r = traer_datos_seguros()
        hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
        
        if p:
            evento = "VIGILANDO"
            res_dolar = "$0.00"
            
            if not st.session_state.comprado and r < 35:
                st.session_state.comprado = True
                st.session_state.entrada = p
                evento = "🛒 COMPRA"
            elif st.session_state.comprado:
                if p >= st.session_state.entrada * (1+(tp/100)) or p <= st.session_state.entrada * (1-(sl/100)):
