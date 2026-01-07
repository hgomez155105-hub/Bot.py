import streamlit as st
from binance.client import Client
import pandas as pd
import time
import requests

# Configuración visual
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")

def obtener_rsi(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=100"
        velas = requests.get(url, timeout=10).json()
        cierres = [float(v[4]) for v in velas]
        ganancias, perdidas = [], []
        for i in range(1, len(cierres)):
            dif = cierres[i] - cierres[i-1]
            ganancias.append(max(dif, 0))
            perdidas.append(abs(min(dif, 0)))
        avg_g = sum(ganancias[-14:]) / 14
        avg_p = sum(perdidas[-14:]) / 14
        if avg_p == 0: return 100
        rs = avg_g / avg_p
        return 100 - (100 / (1 + rs))
    except: return None

# --- LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso al Bot")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if clave == "1234": # <--- PON TU CLAVE AQUÍ
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# --- PANEL DE CONTROL ---
st.title("🤖 Centro de Mando: Scalping 0.80%")

st.sidebar.header("🔑 Configuración")
api_key = st.sidebar.text_input("Binance API Key", type="password")
api_sec = st.sidebar.text_input("Binance Secret", type="password")
par = st.sidebar.selectbox("Moneda", ["SOLUSDT", "BTCUSDT", "ETHUSDT"])

col1, col2, col3 = st.columns(3)
met_precio = col1.empty()
met_rsi = col2.empty()
met_profit = col3.empty()

log_area = st.expander("📝 Registro de Operaciones", expanded=True)

if st.sidebar.button("▶️ ARRANCAR BOT"):
    st.sidebar.success("Bot en línea")
    precio_entrada = 0
    comprado = False
    ganancia_total = 0.0
    
    while True:
        try:
            # 1. Obtener Datos
            url_p = f"https://api.binance.com/api/v3/ticker/price?symbol={par}"
            precio_actual = float(requests.get(url_p).json()['price'])
            rsi_actual = obtener_rsi(par)
            
            # 2. Actualizar Pantalla
            met_precio.metric("Precio SOL", f"${precio_actual:,.2f}")
            if rsi_actual: met_rsi.metric("Sensor RSI", f"{rsi_actual:.2f}")
            met_profit.metric("Ganancia Acumulada", f"${ganancia_total:.4f}")

            # 3. Lógica
            if not comprado:
                if rsi_actual and rsi_actual <= 35:
                    log_area.write(f"🎯 COMPRA detectada a ${precio_actual}")
                    precio_entrada = precio_actual
                    comprado = True
            else:
                dif = ((precio_actual - precio_entrada) / precio_entrada) * 100
                if dif >= 0.80 or dif <= -1.20:
                    tipo = "PROFIT" if dif > 0 else "STOP LOSS"
                    ganancia_total += (10 * (dif / 100)) # Simulación con $10
                    log_area.write(f"🚀 VENTA {tipo} de {dif:.2f}% | Total: ${ganancia_total:.4f}")
                    comprado = False
                    time.sleep(20)

            time.sleep(10)
        except Exception as e:
            st.sidebar.error(f"Error: {e}")
            time.sleep(10)
