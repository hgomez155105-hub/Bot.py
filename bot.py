import streamlit as st
import pandas as pd
import requests
import time

# --- INTERFAZ OSCURA ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-family: 'Courier New', monospace; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

if 'saldo_v' not in st.session_state:
    st.session_state.saldo_v = 1000.0
    st.session_state.log_v = pd.DataFrame(columns=["Hora", "Acción", "Precio", "RSI"])

st.title("🤖 Simulador de Trading (Conexión Híbrida)")

# --- PANEL DE 4 COLUMNAS ---
c1, c2, c3, c4 = st.columns(4)
met_precio = c1.empty()
met_tp = c2.empty()
met_sl = c3.empty()
met_saldo = c4.empty()

st.write("---")
cuadro_estado = st.empty()
tabla_historial = st.empty()

# --- CONEXIÓN HÍBRIDA (BINANCE + COINGECKO) ---
def obtener_precio_maestro(symbol):
    # Intento 1: Binance Futuros (Rápido)
    try:
        res = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}", timeout=3).json()
        return float(res['price']), "Binance"
    except:
        # Intento 2: CoinGecko (Lento pero INFALIBLE)
        try:
            # Simplificamos el nombre para CoinGecko (ej: SOLUSDT -> solana)
            coin = "solana" if "SOL" in symbol else "bitcoin"
            res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd").json()
            return float(res[coin]['usd']), "CoinGecko (Respaldo)"
        except:
            return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Ajustes")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
btn = st.sidebar.button("🚀 INICIAR VIGILANCIA")

if btn:
    cuadro_estado.info("🛰️ Buscando señal de mercado...")
    while True:
        p, fuente = obtener_precio_maestro(par)
        if p:
            val_tp = p * (1 + (tp_p/100))
            val_sl = p * (1 - (sl_p/100))
            rsi_sim = 35 + (p % 25)
            
            # Actualizar Visuales
            met_precio.metric(f"PRECIO {par}", f"${p:,.2f}", f"Fuente: {fuente}")
            met_tp.metric("OBJETIVO PROFIT (VERDE)", f"${val_tp:,.2f}")
            met_sl.metric("STOP LOSS (ROJO)", f"${val_sl:,.2f}")
            met_saldo.metric("SALDO VIRTUAL", f"${st.session_state.saldo_v:,.2f}")
            
            cuadro_estado.success(f"🟢 Conectado vía {fuente}")
            
            # Auto-registro para ver que funciona
            if len(st.session_state.log_v) < 5:
                n = {"Hora": time.strftime("%H:%M:%S"), "Acción": "VIGILANDO", "Precio": p, "RSI": round(rsi_sim, 2)}
                st.session_state.log_v = pd.concat([pd.DataFrame([n]), st.session_state.log_v])
            
            tabla_historial.dataframe(st.session_state.log_v, use_container_width=True)
        else:
            cuadro_estado.error("🔴 Error crítico de red. Reintentando...")
        
        time.sleep(10)
        
