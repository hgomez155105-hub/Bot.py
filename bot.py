import streamlit as st
import pandas as pd
import requests
import time

# --- INTERFAZ NEGRA PRO ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-family: 'Courier New', monospace; font-size: 2.2rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN SEGURA ---
if 'saldo_v' not in st.session_state:
    st.session_state.saldo_v = 1000.0
if 'ganancia_sesion' not in st.session_state:
    st.session_state.ganancia_sesion = 0.0
if 'log_v' not in st.session_state:
    st.session_state.log_v = pd.DataFrame(columns=["Hora", "Evento", "Precio", "P/L Sesión"])

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

# --- CONEXIÓN DE RESPALDO RÁPIDA ---
def get_safe_price(symbol):
    try:
        # Probamos primero la ruta de futuros (más estable)
        res = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}", timeout=5).json()
        return float(res['price']), "Binance"
    except:
        try:
            # Respaldo inmediato si Binance falla
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
    cuadro_estado.info("🛰️ Sincronizando datos de mercado...")
    while True:
        p, fuente = get_safe_price(par)
        if p:
            # Cálculos
            p_tp = p * (1 + (tp_p/100))
            p_sl = p * (1 - (sl_p/100))
            total_actual = st.session_state.saldo_v + st.session_state.ganancia_sesion
            
            # Actualizar tarjetas (Números Blancos)
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}")
            met_tp.metric("OBJETIVO PROFIT", f"${p_tp:,.2f}")
            met_sl.metric("STOP LOSS", f"${p_sl:,.2f}")
            met_saldo.metric("SALDO TOTAL", f"${total_actual:,.2f}")
            
            # Registro en historial (Vigilancia activa)
            if len(st.session_state.log_v) < 1:
                n = {"Hora": time.strftime("%H:%M:%S"), "Evento": "VIGILANDO", "Precio": p, "P/L Sesión": f"${st.session_state.ganancia_sesion:.2f}"}
                st.session_state.log_v = pd.concat([pd.DataFrame([n]), st.session_state.log_v])
            
            cuadro_estado.success(f"🟢 EN LÍNEA | Fuente: {fuente}")
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.warning("🟡 Buscando señal...")
            
        time.sleep(10)
        
