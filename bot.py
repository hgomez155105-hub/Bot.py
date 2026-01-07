import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE HORA ARGENTINA ---
def obtener_hora_arg():
    # Ajuste manual UTC-3 para Buenos Aires
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

# --- INTERFAZ NEGRA Y BLANCA ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    /* Números en Blanco Puro y Grandes */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-family: 'Courier New', monospace; 
        font-size: 2.4rem !important; 
    }
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 1px solid #333; 
        padding: 20px; 
        border-radius: 15px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ANTIFALLOS ---
if 'saldo_base' not in st.session_state:
    st.session_state.saldo_base = 1000.0
if 'ganancia_total' not in st.session_state:
    st.session_state.ganancia_total = 0.0
if 'log_arg' not in st.session_state:
    st.session_state.log_arg = pd.DataFrame(columns=["Hora (ARG)", "Evento", "Precio", "Balance $"])

st.title("🤖 Centro de Mando: Edición Argentina")

# --- PANEL DE 4 COLUMNAS ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_balance = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN ULTRA-ESTABLE ---
def get_price_v5(symbol):
    # Intentamos 3 rutas distintas para que nunca diga "Señal perdida"
    rutas = [
        f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
        f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}",
        f"https://api1.binance.com/api/v3/ticker/price?symbol={symbol}"
    ]
    for r in rutas:
        try:
            res = requests.get(r, timeout=4)
            if res.status_code == 200:
                return float(res.json()['price']), "Estable"
        except: continue
    return None, "Reconectando"

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 ACTIVAR SISTEMA")

if btn:
    while True:
        p, status = get_price_v5(par)
        hora = obtener_hora_arg()
        
        if p:
            p_tp = p * (1 + (tp_p/100))
            p_sl = p * (1 - (sl_p/100))
            # Cálculo de balance corregido para evitar el AttributeError
            total_cash = st.session_state.saldo_base + st.session_state.ganancia_total
            
            # Actualizar Tarjetas Blancas
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_tp.metric("OBJETIVO PROFIT", f"${p_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${p_sl:,.2f}")
            met_balance.metric("BALANCE TOTAL", f"${total_cash:,.2f}")
            
            # Registro en historial con hora de ARG
            if len(st.session_state.log_arg) < 1:
                new_row = {"Hora (ARG)": hora, "Evento": "VIGILANCIA ACTIVA", "Precio": p, "Balance $": f"${total_cash:.2f}"}
                st.session_state.log_arg = pd.concat([pd.DataFrame([new_row]), st.session_state.log_arg]).head(10)
            
            cuadro_estado.success(f"🟢 ONLINE | Hora ARG: {hora} | Señal: {status}")
            tabla_historial.dataframe(st.session_state.log_arg, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Estabilizando señal... No refresque la página.")
        
        time.sleep(10)
            
