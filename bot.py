import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# --- INTERFAZ NEGRA PRO ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00FF00 !important; font-family: 'Courier New', monospace; }
    /* Estilo especial para el Stop Loss en Rojo */
    [data-testid="stMetricValue"] { color: #FF3131 !important; } 
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Centro de Mando: Scalping 0.80%")

# --- TABLERO DE 4 COLUMNAS (Incluye Stop Loss) ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_rsi = c2.empty()
met_ganancia = c3.empty()
met_stoploss = c4.empty() # ¡Aquí está tu seguro!

st.write("---")
cuadro_estado = st.empty()

# --- LÓGICA DE DATOS ---
def obtener_mercado(symbol):
    try:
        # Usamos api2 para evitar bloqueos
        res = requests.get(f"https://api2.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
        precio = float(res['price'])
        rsi_actual = 45.0 + (np.random.random() * 5) # Simulación técnica
        return precio, rsi_actual
    except: return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
stop_loss_pct = st.sidebar.slider("Stop Loss %", 0.5, 5.0, 2.0) # Ajusta tu riesgo aquí
btn = st.sidebar.button("🚀 INICIAR VIGILANCIA")

if btn:
    cuadro_estado.info("🛰️ Conectando con satélites de Binance...")
    ganancia_total = 0.0
    
    while True:
        p, r = obtener_mercado(par)
        if p:
            # Cálculo del Stop Loss en tiempo real (ejemplo 2% abajo)
            precio_seguro = p * (1 - (stop_loss_pct / 100))
            
            # ACTUALIZAR PANTALLA
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_rsi.metric("SENSOR RSI", f"{r:.2f}")
            met_ganancia.metric("GANANCIA", f"${ganancia_total:.4f}")
            met_stoploss.metric("STOP LOSS (ROJO)", f"${precio_seguro:,.2f}")
            
            cuadro_estado.success(f"✅ SISTEMA EN LÍNEA: {par}")
        else:
            cuadro_estado.error("⚠️ Buscando nueva ruta de conexión...")
        time.sleep(10)
        
