import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(page_title="Scalper Bot Pro", layout="wide")

# --- ESTILO PERSONALIZADO ---
st.markdown("""
    <style>
    .reportview-container .main .block-container{ padding-top: 1rem; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Centro de Mando: Scalping 0.80%")

# --- 1. TABLERO DE MÉTRICAS (CENTRO) ---
col1, col2, col3 = st.columns(3)
with col1: met_precio = st.empty()
with col2: met_rsi = st.empty()
with col3: met_ganancia = st.empty()

st.write("---")

# --- 2. ÁREA DE ESTADO CENTRAL ---
st.subheader("📡 Estado del Sistema")
cuadro_estado = st.empty() # Aquí aparecerán los mensajes de conexión

# --- 3. REGISTRO DE OPERACIONES ---
with st.expander("📝 Registro Detallado", expanded=True):
    log_operaciones = st.empty()

# Barra lateral solo para ajustes
st.sidebar.header("⚙️ Configuración")
par = st.sidebar.selectbox("Moneda", ["SOLUSDT", "BTCUSDT"])
btn_inicio = st.sidebar.button("🚀 INICIAR VIGILANCIA")

if btn_inicio:
    cuadro_estado.info("Iniciando conexión segura...")
    ganancia_acumulada = 0.0
    historial = []

    while True:
        try:
            # Usamos un servidor espejo para evitar el bloqueo regional
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={par}"
            res = requests.get(url, timeout=10).json()
            
            if 'price' in res:
                precio = float(res['price'])
                rsi_val = 45.2 # Ejemplo, aquí se calcula tu RSI real
                
                # Actualizar métricas centrales
                met_precio.metric("PRECIO ACTUAL", f"${precio:,.2f}")
                met_rsi.metric("SENSOR RSI", f"{rsi_val:.2f}")
                met_ganancia.metric("GANANCIA TOTAL", f"${ganancia_acumulada:.4f}")
                
                cuadro_estado.success(f"✅ Conectado y Vigilando {par}")
            else:
                cuadro_estado.warning("⚠️ Binance limitó la conexión. Reintentando...")
            
        except Exception as e:
            cuadro_estado.error(f"❌ Error de Conexión: Reintentando en 10s...")
        
        time.sleep(10)
        
