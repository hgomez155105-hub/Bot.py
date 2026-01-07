import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.title("🤖 Centro de Mando: Scalping 0.80%")

# Espacios fijos para que no desaparezcan los datos
col1, col2, col3 = st.columns(3)
met_precio = col1.empty()
met_rsi = col2.empty()
met_ganancia = col3.empty()

def obtener_datos_libres(symbol):
    try:
        # Usamos el endpoint de datos públicos que suele saltar restricciones
        url_p = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        url_k = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
        
        p_res = requests.get(url_p, timeout=5).json()
        k_res = requests.get(url_k, timeout=5).json()
        
        precio = float(p_res['price'])
        cierres = np.array([float(v[4]) for v in k_res])
        
        # Cálculo de RSI manual
        diff = np.diff(cierres)
        gain = (diff > 0) * diff
        loss = (diff < 0) * -diff
        avg_gain = np.mean(gain[-14:])
        avg_loss = np.mean(loss[-14:])
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        return precio, rsi
    except:
        return None, None

# --- SIDEBAR ---
st.sidebar.header("🔑 Configuración")
par = st.sidebar.selectbox("Moneda", ["SOLUSDT", "BTCUSDT"])
btn_inicio = st.sidebar.button("▶️ ARRANCAR BOT")

if btn_inicio:
    st.sidebar.success("Bot en modo Vigilancia")
    ganancia_total = 0.0
    
    while True:
        precio, rsi = obtener_datos_libres(par)
        
        if precio:
            met_precio.metric("Precio Actual", f"${precio:,.2f}")
            met_rsi.metric("Sensor RSI", f"{rsi:.2f}")
            met_ganancia.metric("Ganancia Total", f"${ganancia_total:.4f}")
            
            # Aquí iría tu lógica de compra/venta
            if rsi <= 35:
                st.toast(f"🎯 Oportunidad detectada en {par}")
        else:
            st.sidebar.error("Reconectando con Binance...")
        
        time.sleep(10)
              
