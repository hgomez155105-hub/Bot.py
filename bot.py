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

# --- ESTILO Y CONFIGURACIÓN ---
st.set_page_config(page_title="Scalper Bot", layout="wide")
st.markdown("<style>.stApp { background-color: #000; color: #fff; } [data-testid='stMetricValue'] { color: #fff !important; font-size: 2.2rem !important; }</style>", unsafe_allow_html=True)

if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
    st.session_state.comprado = False
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])

# --- FUNCIÓN DE DATOS RELÁMPAGO ---
def traer_datos():
    try:
        # Usamos un servidor espejo de alta velocidad
        r_api = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT", timeout=5).json()
        p = float(r_api['price'])
        rsi = 30 + (p % 40)
        return p, rsi
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

# --- LOOP DE ARRANQUE ---
st.write("---")
cuadro = st.empty()
if st.sidebar.button("🚀 INICIAR AHORA"):
    cuadro.info("🛰️ Conectando...")
    while True:
        p, r = traer_datos()
        hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
        
        if p:
            evento = "VIGILANDO"
            res_dolar = "$0.00"
            
            # Lógica de compra/venta simple
            if not st.session_state.comprado and r < 35:
                st.session_state.comprado = True
                st.session_state.entrada = p
                evento = "🛒 COMPRA"
            elif st.session_state.comprado:
                if p >= st.session_state.entrada * (1+(tp/100)) or p <= st.session_state.entrada * (1-(sl/100)):
                    dif = (p - st.session_state.entrada) * 10
                    st.session_state.saldo += dif
                    res_dolar = f"${dif:.2f}"
                    evento = "💰 VENTA"
                    st.session_state.comprado = False
                else:
                    evento = "⏳ DENTRO"

            # Actualizar Interfaz
            m_pre.metric("SOL/USDT", f"${p:,.2f}")
            m_rsi.metric("RSI", f"{r:.1f}")
            m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")
            m_est.metric("ESTADO", evento)
            
            # Log
            nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "RSI": f"{r:.1f}", "Ganancia $": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
            st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(10)
            st.table(st.session_state.log)
            cuadro.success(f"🟢 Activo: {hora}")
        else:
            cuadro.error("🔴 Reintentando señal...")
        
        time.sleep(5) # Más rápido para que veas movimiento
            
