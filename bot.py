import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- SEGURIDAD ---
PASSWORD = "caseros2024"
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if clave == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# --- ESTILO COMPACTO ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.6rem !important; font-weight: 400 !important; }
    [data-testid="stMetricLabel"] { color: #CCCCCC !important; font-size: 0.85rem !important; }
    .stTable, [data-testid="stTable"] td { color: #FFFFFF !important; font-size: 0.9rem !important; font-weight: 600 !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False
    st.session_state.entrada = 0.0
    st.session_state.stop_fijo = 0.0
if 'moneda_actual' not in st.session_state:
    st.session_state.moneda_actual = "SOL"

# --- SIDEBAR (CONTROLES MANUALES) ---
st.sidebar.header("⚙️ Configuración Pro")
moneda_nueva = st.sidebar.selectbox("Seleccionar Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])

if moneda_nueva != st.session_state.moneda_actual:
    st.session_state.moneda_actual = moneda_nueva
    st.session_state.comprado = False 
    st.rerun()

# 1. CAMBIO DE MONTO MANUAL
monto_trade = st.sidebar.number_input("Monto por Operación (USD):", min_value=1.0, max_value=1000.0, value=10.0, step=1.0)

# 2. RSI REGULABLE MANUAL
st.sidebar.write("---")
st.sidebar.write("**Niveles de RSI**")
rsi_compra = st.sidebar.slider("RSI Compra (Entrada):", 10, 50, 30)
rsi_venta = st.sidebar.slider("RSI Venta (Salida):", 51, 90, 60)

st.sidebar.write("---")
sl_p = st.sidebar.slider("Stop Loss % (Seguridad)", 0.1, 10.0, 2.0)
encendido = st.sidebar.toggle("🚀 ACTIVAR BOT", value=False)

if st.sidebar.button("🗑️ Limpiar Historial"):
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia", "Billetera"])
    st.rerun()

# --- DATOS ---
def traer_datos(symbol):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        p = float(res['USD'])
        # Simulación dinámica para pruebas
        rsi_sim = 20 + (p * 100 % 65) 
        return p, rsi_sim
    except: return None, None

# --- PANEL PRINCIPAL ---
st.title(f"🤖 Scalper Pro: {st.session_state.moneda_actual}")

c1, c2, c3, c4 = st.columns(4)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()
m_est = c4.empty()

st.write(f"### Estrategia: {rsi_compra} RSI / {rsi_venta} RSI")
c5, c6 = st.columns(2)
m_objetivo = c5.empty()
m_stop = c6.empty()

st.write("---")
cuadro_estado = st.empty()

# --- LÓGICA ---
if encendido:
    p, r = traer_datos(st.session_state.moneda_actual)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
    
    if p:
        evento = "VIGILANDO"
        res_dolar = "$0.00"
        
        # 1. COMPRA (Usa el valor manual rsi_compra)
        if not st.session_state.comprado:
            if r <= rsi_compra:
                st.session_state.comprado = True
                st.session_state.entrada = p
                st.session_state.stop_fijo = p * (1 - (sl_p/100))
                evento = f"🛒 COMPRA (${monto_trade})"
        
        # 2. VENTA (Usa el valor manual rsi_venta)
        else:
            if r >= rsi_venta:
                dif = (p - st.session_state.entrada) * (monto_trade/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"+${dif:.2f}"
                evento = f"💰 PROFIT (RSI > {rsi_venta})"
                st.session_state.comprado = False
            elif p <= st.session_state.stop_fijo:
                dif = (p - st.session_state.entrada) * (monto_trade/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"${dif:.2f}"
                evento = "📉 STOP LOSS"
                st.session_state.comprado = False
            else:
                evento = f"⏳ HOLD (Invertido: ${monto_trade})"

        # Actualizar UI
        m_pre.metric("PRECIO ACTUAL", f"${p:,.2f}")
        m_rsi.metric("SENSOR RSI", f"{r:.1f}")
        m_bil.metric("SALDO TOTAL", f"${st.session_state.saldo:,.2f}")
        m_est.metric("ESTADO BOT", evento)
        
        m_objetivo.metric("META DE SALIDA", f"RSI > {rsi_venta}")
        m_stop.metric("STOP LOSS ACTIVO", f"${st.session_state.stop_fijo:,.2f}" if st.session_state.comprado else "ESPERANDO...")
        
        nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "RSI": f"{r:.1f}", "Ganancia": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(10)
        st.table(st.session_state.log)
        
        cuadro_estado.success(f"🟢 Conectado | Monto: ${monto_trade} | RSI: {rsi_compra}-{rsi_venta} | {hora}")
        
        time.sleep(10)
        st.rerun()
else:
    cuadro_estado.warning("🔴 Bot Apagado.")
