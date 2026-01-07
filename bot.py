import streamlit as st
import pandas as pd
import requests
import time

# --- INTERFAZ NEGRA CON NÚMEROS BLANCOS ---
st.set_page_config(page_title="Scalper Bot Pro - SIMULADOR", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    /* Forzamos que todos los números de métricas sean Blancos */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-family: 'Courier New', monospace; 
        font-size: 2.2rem !important; 
    }
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 1px solid #333; 
        padding: 15px; 
        border-radius: 12px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAR VARIABLES DE SESIÓN ---
if 'saldo_v' not in st.session_state:
    st.session_state.saldo_v = 1000.0
    st.session_state.ganancia_sesion = 0.0
    st.session_state.log_v = pd.DataFrame(columns=["Hora", "Evento", "Precio", "Ganancia Día $"])

st.title("🤖 Centro de Mando: Simulación Pro")

# --- PANEL SUPERIOR ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_saldo = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN MULTI-RUTA ---
def obtener_datos_pro(symbol):
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
        res = requests.get(url, timeout=5).json()
        return float(res['price']), "Binance"
    except:
        try:
            coin = "solana" if "SOL" in symbol else "bitcoin"
            res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd").json()
            return float(res[coin]['usd']), "Respaldo"
        except:
            return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Estrategia")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR")

if btn:
    while True:
        p, fuente = obtener_datos_pro(par)
        if p:
            # Cálculos de niveles
            val_tp = p * (1 + (tp_p/100))
            val_sl = p * (1 - (sl_p/100))
            
            # Actualizar Tarjetas (Ahora en BLANCO)
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_tp.metric("OBJETIVO PROFIT", f"${val_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${val_sl:,.2f}")
            met_saldo.metric("SALDO + GANANCIA", f"${st.session_state.saldo_v + st.session_state.ganancia_sesion:,.2f}")
            
            # Lógica de Registro (Opción B)
            if len(st.session_state.log_v) < 10:
                # Simulación de un cierre de profit para ver el historial funcionar
                if p >= val_tp: st.session_state.ganancia_sesion += 5.0 
                
                n = {"Hora": time.strftime("%H:%M:%S"), 
                     "Evento": "VIGILANDO", 
                     "Precio": p, 
                     "Ganancia Día $": f"+${st.session_state.ganancia_sesion:.2f}"}
                st.session_state.log_v = pd.concat([pd.DataFrame([n]), st.session_state.log_v]).head(10)
            
            cuadro_estado.success(f"🟢 SISTEMA ACTIVO | Fuente: {fuente}")
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Reconectando...")
            
        time.sleep(10)
        
