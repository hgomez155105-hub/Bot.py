import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(page_title="Scalper Bot Pro", layout="wide")

# --- INTERFAZ ---
st.title("🤖 Centro de Mando: Scalping 0.80%")

col1, col2, col3 = st.columns(3)
met_precio = col1.empty()
met_rsi = col2.empty()
met_ganancia = col3.empty()

st.write("---")
cuadro_estado = st.empty()

# --- BARRA LATERAL (CONFIGURACIÓN DE MONEDAS) ---
st.sidebar.header("⚙️ Configuración")
# Aquí puedes escribir CUALQUIER moneda (ej: ETHUSDT, DOGEUSDT, ADAUSDT)
par = st.sidebar.text_input("Escribe el Par de Binance", value="SOLUSDT").upper()
btn_inicio = st.sidebar.button("🚀 INICIAR VIGILANCIA")

def obtener_datos(symbol):
    try:
        # Usamos api1 o api2 para saltar bloqueos regionales
        url_p = f"https://api1.binance.com/api/v3/ticker/price?symbol={symbol}"
        url_k = f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
        
        p_res = requests.get(url_p, timeout=5).json()
        k_res = requests.get(url_k, timeout=5).json()
        
        precio = float(p_res['price'])
        cierres = np.array([float(v[4]) for v in k_res])
        
        diff = np.diff(cierres)
        gain = (diff > 0) * diff
        loss = (diff < 0) * -diff
        rs = np.mean(gain[-14:]) / np.mean(loss[-14:])
        rsi = 100 - (100 / (1 + rs))
        
        return precio, rsi
    except:
        return None, None

if btn_inicio:
    cuadro_estado.info(f"Conectando con {par}...")
    ganancia_total = 0.0
    
    while True:
        precio, rsi = obtener_datos(par)
        
        if precio:
            met_precio.metric(f"Precio {par}", f"${precio:,.2f}")
            met_rsi.metric("Sensor RSI", f"{rsi:.2f}")
            met_ganancia.metric("Ganancia Total", f"${ganancia_total:.4f}")
            cuadro_estado.success(f"✅ Vigilando {par} en tiempo real")
        else:
            cuadro_estado.error("⚠️ Error de conexión regional. Reintentando...")
        
        time.sleep(10)
        
