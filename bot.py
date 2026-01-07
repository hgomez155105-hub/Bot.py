import streamlit as st
import pandas as pd
import requests
import time

# --- INTERFAZ OSCURA TOTAL ---
st.set_page_config(page_title="Scalper Bot Pro - SIMULADOR", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    /* Colores para las tarjetas */
    [data-testid="stMetricValue"] { font-family: 'Courier New', monospace; font-size: 1.8rem !important; }
    div[data-testid="stMetric"]:nth-child(1) [data-testid="stMetricValue"] { color: #FFFFFF !important; } /* Precio */
    div[data-testid="stMetric"]:nth-child(2) [data-testid="stMetricValue"] { color: #00FF00 !important; } /* Profit */
    div[data-testid="stMetric"]:nth-child(3) [data-testid="stMetricValue"] { color: #FF3131 !important; } /* Stop */
    div[data-testid="stMetric"]:nth-child(4) [data-testid="stMetricValue"] { color: #00D1FF !important; } /* Saldo */
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

if 'saldo_v' not in st.session_state:
    st.session_state.saldo_v = 1000.0
    st.session_state.log_v = pd.DataFrame(columns=["Hora", "Acción", "Precio", "Resultado $"])

st.title("🤖 Simulador de Trading Real (Camino A)")

# --- PANEL SUPERIOR DE 4 COLUMNAS ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_saldo = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN DE ALTA ESTABILIDAD ---
def get_data_v4(symbol):
    # Usamos el servidor de datos de futuros que es más abierto
    url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
    try:
        res = requests.get(url, timeout=10).json()
        return float(res['price'])
    except:
        return None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes de Estrategia")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR SIMULACIÓN")

if btn:
    cuadro_estado.success(f"🟢 SISTEMA ACTIVADO: Monitoreando {par}")
    while True:
        p = get_data_v4(par)
        if p:
            # Cálculos de objetivos
            val_tp = p * (1 + (tp_p/100))
            val_sl = p * (1 - (sl_p/100))
            
            # Actualizar tarjetas superiores
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_tp.metric("OBJETIVO PROFIT", f"${val_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${val_sl:,.2f}")
            met_saldo.metric("SALDO VIRTUAL", f"${st.session_state.saldo_v:,.2f}")
            
            # Registro automático inicial
            if len(st.session_state.log_v) < 1:
                nuevo = {"Hora": time.strftime("%H:%M:%S"), "Acción": "VIGILANCIA", "Precio": p, "Resultado $": 0}
                st.session_state.log_v = pd.concat([pd.DataFrame([nuevo]), st.session_state.log_v])
            
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Reconectando con túnel de datos...")
        
        time.sleep(10)
        
