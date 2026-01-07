import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE HORA ARGENTINA ---
def obtener_hora_ba():
    # UTC-3 para Argentina
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

# --- INTERFAZ NEGRA PRO ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-family: 'Courier New', monospace; font-size: 2.2rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'log_v' not in st.session_state:
    st.session_state.log_v = pd.DataFrame(columns=["Hora (ARG)", "Evento", "Precio", "P/L"])

st.title("🤖 Centro de Mando: Conexión Argentina")

# --- PANEL SUPERIOR ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_reloj = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN REFORZADA ANTIBLOQUEO ---
def get_price_stable(symbol):
    # Lista de servidores espejo para rotar si uno falla
    urls = [
        f"https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
        f"https://api2.binance.com/api/v3/ticker/price?symbol={symbol}",
        f"https://api3.binance.com/api/v3/ticker/price?symbol={symbol}",
        f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                return float(res.json()['price']), "Estable"
        except:
            continue
    return None, "Inestable"

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR VIGILANCIA")

if btn:
    cuadro_estado.info(f"🛰️ Sincronizando con hora de Argentina ({obtener_hora_ba()})...")
    while True:
        p, estado = get_price_stable(par)
        hora_actual = obtener_hora_ba()
        
        if p:
            p_tp = p * (1 + (tp_p/100))
            p_sl = p * (1 - (sl_p/100))
            
            # Actualizar tarjetas (Todo en Blanco)
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_tp.metric("OBJETIVO PROFIT", f"${p_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${p_sl:,.2f}")
            met_reloj.metric("HORA ARG", hora_actual)
            
            # Registrar en historial con hora de Argentina
            if len(st.session_state.log_v) < 10:
                n = {"Hora (ARG)": hora_actual, "Evento": "VIGILANDO", "Precio": p, "P/L": "$0.00"}
                st.session_state.log_v = pd.concat([pd.DataFrame([n]), st.session_state.log_v]).head(10)
            
            cuadro_estado.success(f"🟢 SISTEMA ONLINE | Señal: {estado}")
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.warning("🔴 Señal perdida. Rotando servidores de respaldo...")
            time.sleep(2) # Reintento rápido
        
        time.sleep(8) # Pausa equilibrada para no ser bloqueado
