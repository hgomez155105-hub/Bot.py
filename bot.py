import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(page_title="Scalper Bot Pro - SIMULADOR", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-family: 'Courier New', monospace; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAR BILLETERA VIRTUAL ---
if 'saldo_usd' not in st.session_state:
    st.session_state.saldo_usd = 1000.0
    st.session_state.posicion_abierta = False
    st.session_state.precio_compra = 0.0
    st.session_state.log_sim = pd.DataFrame(columns=["Hora", "Acción", "Precio", "RSI", "Resultado $"])

st.title("🤖 Simulador de Trading Real (Camino A)")

# --- PANEL DE MÉTRICAS ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_rsi = c2.empty()
met_saldo = c3.empty()
met_estado = c4.empty()

st.write("---")
cuadro_estado = st.empty()
st.subheader("📝 Historial de Operaciones Simuladas")
tabla_historial = st.empty()

# --- LÓGICA DE CONEXIÓN ---
def obtener_datos():
    try:
        url = "https://api1.binance.com/api/v3/ticker/price?symbol=" + par
        res = requests.get(url, timeout=5).json()
        p = float(res['price'])
        r = 30 + (p % 40) # RSI técnico simulado
        return p, r
    except: return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes de Simulación")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_pct = st.sidebar.slider("Take Profit %", 0.1, 5.0, 0.8)
sl_pct = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR SIMULACIÓN")

if btn:
    while True:
        p, r = obtener_datos()
        if p:
            # 1. LÓGICA DE COMPRA (Si no hay posición y RSI es bajo)
            if not st.session_state.posicion_abierta and r < 35:
                st.session_state.posicion_abierta = True
                st.session_state.precio_compra = p
                nuevo = {"Hora": time.strftime("%H:%M:%S"), "Acción": "COMPRA", "Precio": p, "RSI": r, "Resultado $": 0}
                st.session_state.log_sim = pd.concat([pd.DataFrame([nuevo]), st.session_state.log_sim])
            
            # 2. LÓGICA DE VENTA (Take Profit o Stop Loss)
            elif st.session_state.posicion_abierta:
                p_ganancia = st.session_state.precio_compra * (1 + (tp_pct/100))
                p_perdida = st.session_state.precio_compra * (1 - (sl_pct/100))
                
                if p >= p_ganancia or p <= p_perdida:
                    resultado = (p - st.session_state.precio_compra) * 10 # Simulando compra de 10 monedas
                    st.session_state.saldo_usd += resultado
                    st.session_state.posicion_abierta = False
                    tipo_venta = "VENTA PROFIT" if p >= p_ganancia else "VENTA STOP"
                    nuevo = {"Hora": time.strftime("%H:%M:%S"), "Acción": tipo_venta, "Precio": p, "RSI": r, "Resultado $": round(resultado, 2)}
                    st.session_state.log_sim = pd.concat([pd.DataFrame([nuevo]), st.session_state.log_sim])

            # Actualizar Visuales
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_rsi.metric("SENSOR RSI", f"{r:.2f}")
            met_saldo.metric("SALDO VIRTUAL", f"${st.session_state.saldo_usd:,.2f}")
            estado_txt = "BUSCANDO COMPRA" if not st.session_state.posicion_abierta else "DENTRO DEL TRADE"
            met_estado.metric("ESTADO", estado_txt)
            
            tabla_historial.dataframe(st.session_state.log_sim, use_container_width=True)
            
        time.sleep(10)
            
