import streamlit as st
import pandas as pd
import requests
import time

# --- INTERFAZ OSCURA PROFESIONAL ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-family: 'Courier New', monospace; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

if 'saldo_v' not in st.session_state:
    st.session_state.saldo_v = 1000.0
    st.session_state.log_v = pd.DataFrame(columns=["Hora", "Acción", "Precio", "Fuente"])

st.title("🤖 Centro de Mando: Conexión Reforzada")

# --- PANEL DE CONTROL ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_saldo = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- MOTOR DE CONEXIÓN TRIPLE SALTO ---
def obtener_precio_infalible(symbol):
    # Intento 1: Binance
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=3).json()
        return float(res['price']), "Binance"
    except:
        # Intento 2: Respaldo Coingecko
        try:
            coin = "solana" if "SOL" in symbol else "bitcoin"
            res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd").json()
            return float(res[coin]['usd']), "CoinGecko"
        except:
            return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 RECONECTAR SISTEMA")

if btn:
    cuadro_estado.info("🛰️ Reestableciendo túnel de datos...")
    while True:
        p, fuente = obtener_precio_infalible(par)
        if p:
            val_tp = p * (1 + (tp_p/100))
            val_sl = p * (1 - (sl_p/100))
            
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}", f"vía {fuente}")
            met_tp.metric("OBJETIVO PROFIT", f"${val_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${val_sl:,.2f}")
            met_saldo.metric("SALDO VIRTUAL", f"${st.session_state.saldo_v:,.2f}")
            
            cuadro_estado.success(f"🟢 CONECTADO: Datos fluyendo desde {fuente}")
            
            # Registro de vida en historial
            if len(st.session_state.log_v) < 1:
                n = {"Hora": time.strftime("%H:%M:%S"), "Acción": "RECONEXIÓN", "Precio": p, "Fuente": fuente}
                st.session_state.log_v = pd.concat([pd.DataFrame([n]), st.session_state.log_v])
            
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.error("🔴 Error de red persistente. Reintentando...")
        
        time.sleep(10)
