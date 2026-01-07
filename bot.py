import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE HORA Y ESTILO ---
def hora_arg():
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.2rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- MEMORIA DEL SISTEMA ---
if 'log_completo' not in st.session_state:
    st.session_state.log_completo = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Estado"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False
    st.session_state.precio_entrada = 0.0
    st.session_state.ganancia_acumulada = 0.0

st.title("🤖 Centro de Mando: Simulación Integral")

# --- PANEL SUPERIOR ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_rsi = c2.empty()
met_tp = c3.empty()
met_sl = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN DE DATOS ---
def obtener_datos_v6():
    try:
        url = "https://min-api.cryptocompare.com/data/price?fsym=SOL&tsyms=USD"
        p = float(requests.get(url, timeout=5).json()['USD'])
        # RSI Simulado basado en micro-tendencia para la simulación
        r = 30 + (p % 40) 
        return p, r
    except: return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes de Estrategia")
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR SESIÓN")

if btn:
    while True:
        p, r = obtener_datos_v6()
        if p:
            # Cálculos de Niveles
            p_tp = p * (1 + (tp_p/100))
            p_sl = p * (1 - (sl_p/100))
            
            evento = "VIGILANDO"
            ganancia_actual = f"${st.session_state.ganancia_acumulada:.2f}"
            
            # LÓGICA DE TRADING
            # 1. Compra si RSI es bajo y no estamos comprados
            if not st.session_state.comprado and r < 40:
                st.session_state.comprado = True
                st.session_state.precio_entrada = p
                evento = "🛒 COMPRA"
            
            # 2. Venta por TP o SL si estamos comprados
            elif st.session_state.comprado:
                target = st.session_state.precio_entrada * (1 + (tp_p/100))
                stop = st.session_state.precio_entrada * (1 - (sl_p/100))
                
                if p >= target:
                    res = (p - st.session_state.precio_entrada) * 10 # Simula 10 SOL
                    st.session_state.ganancia_acumulada += res
                    st.session_state.comprado = False
                    evento = "💰 VENTA (PROFIT)"
                elif p <= stop:
                    res = (p - st.session_state.precio_entrada) * 10
                    st.session_state.ganancia_acumulada += res
                    st.session_state.comprado = False
                    evento = "📉 VENTA (STOP)"
                else:
                    evento = "⏳ HOLD (DENTRO)"

            # ACTUALIZAR MÉTRICAS (BLANCAS)
            met_precio.metric("PRECIO SOL", f"${p:,.2f}")
            met_rsi.metric("SENSOR RSI", f"{r:.1f}")
            met_tp.metric("OBJETIVO TP", f"${p_tp:,.2f}")
            met_sl.metric("PROTECCIÓN SL", f"${p_sl:,.2f}")
            
            # ACTUALIZAR TABLA MAESTRA
            # Solo agregamos a la tabla si hay un cambio o cada cierto tiempo para no saturar
            nuevo_log = {
                "Hora": hora_arg(),
                "Evento": evento,
                "Precio": f"${p:,.2f}",
                "RSI": f"{r:.1f}",
                "Ganancia $": f"${st.session_state.ganancia_acumulada:.2f}",
                "Estado": "POSICIÓN ABIERTA" if st.session_state.comprado else "BUSCANDO"
            }
            st.session_state.log_completo = pd.concat([pd.DataFrame([nuevo_log]), st.session_state.log_completo]).head(15)
            
            cuadro_estado.success(f"🟢 SISTEMA OPERATIVO | HORA ARG: {hora_arg()}")
            tabla_historial.dataframe(st.session_state.log_completo, use_container_width=True)
            
        time.sleep(10)
            
