import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

# Configuración de página
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")

# Título y Diseño Central
st.title("🤖 Centro de Mando: Scalping 0.80%")

col1, col2, col3 = st.columns(3)
met_precio = col1.empty()
met_rsi = col2.empty()
met_ganancia = col3.empty()

st.write("---")
cuadro_estado = st.empty()

# Barra Lateral
st.sidebar.header("⚙️ Configuración")
par = st.sidebar.text_input("Moneda (ej: SOLUSDT)", value="SOLUSDT").upper()
btn_inicio = st.sidebar.button("🚀 INICIAR VIGILANCIA")

def obtener_datos_sin_bloqueo(symbol):
    try:
        # Usamos el endpoint de 'ticker/24hr' que es más permisivo con las regiones
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        data = requests.get(url, timeout=10).json()
        
        # Si esto falla, intentamos con un servidor espejo (api3)
        if 'lastPrice' not in data:
            url = f"https://api3.binance.com/api/v3/ticker/price?symbol={symbol}"
            data = requests.get(url, timeout=10).json()
            precio = float(data['price'])
        else:
            precio = float(data['lastPrice'])
            
        # Obtenemos velas para el RSI de un servidor espejo
        url_k = f"https://api3.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
        velas = requests.get(url_k, timeout=10).json()
        cierres = np.array([float(v[4]) for v in velas])
        
        # Cálculo de RSI
        diff = np.diff(cierres)
        gain = (diff > 0) * diff
        loss = (diff < 0) * -diff
        avg_gain = np.mean(gain[-14:])
        avg_loss = np.mean(loss[-14:])
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        return precio, rsi
    except Exception as e:
        return None, None

if btn_inicio:
    cuadro_estado.info(f"Conectando con {par} vía Servidor Espejo...")
    ganancia_total = 0.0
    
    while True:
        precio, rsi = obtener_datos_sin_bloqueo(par)
        
        if precio:
            met_precio.metric(f"Precio {par}", f"${precio:,.2f}")
            met_rsi.metric("Sensor RSI", f"{rsi:.2f}")
            met_ganancia.metric("Ganancia Total", f"${ganancia_total:.4f}")
            cuadro_estado.success(f"✅ Conexión Exitosa: Vigilando {par}")
        else:
            cuadro_estado.warning("⚠️ Intentando saltar bloqueo regional de Binance...")
            
        time.sleep(10)
        
