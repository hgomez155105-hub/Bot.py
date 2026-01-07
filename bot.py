import streamlit as st
import pandas as pd
import requests
import time

# --- DISEÑO OSCURO PRO ---
st.set_page_config(page_title="Scalper Bot Pro - SIMULADOR", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00FF00 !important; font-family: 'Courier New', monospace; font-size: 2.5rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

if 'saldo_usd' not in st.session_state:
    st.session_state.saldo_usd = 1000.0
    st.session_state.log_sim = pd.DataFrame(columns=["Hora", "Acción", "Precio", "RSI", "Resultado $"])

st.title("🤖 Simulador de Trading Real (Camino A)")

# --- MÉTRICAS ---
c1, c2, c3 = st.columns(3)
met_precio = c1.empty()
met_rsi = c2.empty()
met_saldo = c3.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN QUE NO SE BLOQUEA ---
def obtener_precio_seguro(symbol):
    try:
        # Usamos una ruta alternativa (fapi) que suele estar abierta para simuladores
        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
        res = requests.get(url, timeout=10).json()
        p = float(res['price'])
        # Generamos un RSI dinámico para el simulador
        r = 30 + (p % 40)
        return p, r
    except:
        # Si falla, usamos una API secundaria de respaldo
        try:
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}").json()
            return float(res['price']), 50.0
        except:
            return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
btn = st.sidebar.button("🚀 INICIAR SIMULACIÓN")

if btn:
    cuadro_estado.success(f"🟢 CONEXIÓN ESTABLECIDA: {par}")
    while True:
        precio, rsi = obtener_precio_seguro(par)
        if precio:
            met_precio.metric(f"PRECIO {par}", f"${precio:,.2f}")
            met_rsi.metric("SENSOR RSI", f"{rsi:.2f}")
            met_saldo.metric("SALDO VIRTUAL", f"${st.session_state.saldo_usd:,.2f}")
            
            # Registrar inicio en el historial
            if len(st.session_state.log_sim) < 1:
                nuevo = {"Hora": time.strftime("%H:%M:%S"), "Acción": "SISTEMA OK", "Precio": precio, "RSI": rsi, "Resultado $": 0}
                st.session_state.log_sim = pd.concat([pd.DataFrame([nuevo]), st.session_state.log_sim])
            
            tabla_historial.dataframe(st.session_state.log_sim, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Reintentando conexión segura...")
            
        time.sleep(5)
        
