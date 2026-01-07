import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- HORA ARGENTINA ---
def hora_arg():
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

# --- DISEÑO BLANCO SOBRE NEGRO ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.5rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

if 'log_v' not in st.session_state:
    st.session_state.log_v = pd.DataFrame(columns=["Hora (ARG)", "Evento", "Precio", "Balance $"])

st.title("🤖 Centro de Mando: Conexión Argentina")

# --- PANEL SUPERIOR ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_balance = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN INFALIBLE (SIN BLOQUEO DE BINANCE) ---
def get_price_bypass(symbol):
    try:
        # Usamos el API de CryptoCompare que no bloquea a Streamlit
        coin = symbol.replace("USDT", "")
        url = f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        return float(res['USD']), "Túnel Seguro"
    except:
        return None, "Buscando..."

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 ACTIVAR SISTEMA")

if btn:
    cuadro_estado.info(f"🛰️ Iniciando sistema en Buenos Aires... {hora_arg()}")
    while True:
        p, fuente = get_price_bypass(par)
        if p:
            # Cálculos de Niveles
            p_tp = p * (1 + (tp_p/100))
            p_sl = p * (1 - (sl_p/100))
            
            # Actualizar Tarjetas Blancas
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_tp.metric("OBJETIVO PROFIT", f"${p_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${p_sl:,.2f}")
            met_balance.metric("SALDO INICIAL", "$1,000.00")
            
            # Registro en Historial
            if len(st.session_state.log_v) < 10:
                n = {"Hora (ARG)": hora_arg(), "Evento": "SEÑAL OK", "Precio": p, "Balance $": "$1,000.00"}
                st.session_state.log_v = pd.concat([pd.DataFrame([n]), st.session_state.log_v]).head(10)
            
            cuadro_estado.success(f"🟢 CONECTADO | Fuente: {fuente} | Hora: {hora_arg()}")
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Sincronizando con la red... Por favor espere.")
        
        time.sleep(10)
        
