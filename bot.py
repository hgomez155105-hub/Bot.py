import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(page_title="Scalper Bot Pro - SIMULADOR", layout="wide")

# --- DISEÑO OSCURO TOTAL ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00FF00 !important; font-family: 'Courier New', monospace; font-size: 2.2rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAR VARIABLES ---
if 'saldo_usd' not in st.session_state:
    st.session_state.saldo_usd = 1000.0
    st.session_state.log_sim = pd.DataFrame(columns=["Hora", "Acción", "Precio", "RSI", "Resultado $"])

st.title("🤖 Simulador de Trading Real (Camino A)")

# --- MÉTRICAS SUPERIORES ---
c1, c2, c3 = st.columns(3)
met_precio = c1.empty()
met_rsi = c2.empty()
met_saldo = c3.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN DE ALTA VELOCIDAD ---
def obtener_precio_sim(symbol):
    try:
        # Probamos con el servidor 'api' más rápido
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
        p = float(res['price'])
        # Generamos un RSI volátil para que veas movimientos rápido
        r = 30 + (time.time() % 40) 
        return p, r
    except:
        return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR SIMULACIÓN")

if btn:
    cuadro_estado.success(f"🟢 Simulador Activo: Monitoreando {par}")
    while True:
        precio, rsi = obtener_precio_sim(par)
        if precio:
            # Actualizar visuales
            met_precio.metric(f"PRECIO {par}", f"${precio:,.2f}")
            met_rsi.metric("SENSOR RSI", f"{rsi:.2f}")
            met_saldo.metric("SALDO VIRTUAL", f"${st.session_state.saldo_usd:,.2f}")
            
            # Registrar evento de vigilancia en el historial para ver que "está vivo"
            if len(st.session_state.log_sim) < 1:
                nuevo = {"Hora": time.strftime("%H:%M:%S"), "Acción": "INICIO", "Precio": precio, "RSI": rsi, "Resultado $": 0}
                st.session_state.log_sim = pd.concat([pd.DataFrame([nuevo]), st.session_state.log_sim])
            
            tabla_historial.dataframe(st.session_state.log_sim, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Conectando con servidor espejo...")
            
        time.sleep(5) # Actualización más rápida cada 5 segundos
