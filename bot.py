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
st.set_page_config(page_title="Scalper Bot", layout="wide")
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
    st.session_state.target_fijo = 0.0
    st.session_state.stop_fijo = 0.0
if 'moneda_actual' not in st.session_state:
    st.session_state.moneda_actual = "SOL"

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
moneda_nueva = st.sidebar.selectbox("Seleccionar Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])

if moneda_nueva != st.session_state.moneda_actual:
    st.session_state.moneda_actual = moneda_nueva
    st.session_state.comprado = False 
    st.rerun()

monto_trade = 10.0
tp_p = st.sidebar.slider("Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Loss %", 0.1, 5.0, 2.0)
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
        rsi_sim = 30 + (p % 40) # Simulación de RSI basada en precio
        return p, rsi_sim
    except: return None, None

# --- PANEL PRINCIPAL ---
st.title(f"🤖 Monitor: {st.session_state.moneda_actual}")

# Fila de Métricas Principales (Ahora con RSI)
c1, c2, c3, c4 = st.columns(4)
m_pre = c1.empty()
m_rsi = c2.empty() # Sensor RSI recuperado
m_bil = c3.empty()
m_est = c4.empty()

st.write("### Niveles de Ejecución (Fijos)")
c5, c6 = st.columns(2)
m_target = c5.empty()
m_stop = c6.empty()

st.write("---")
cuadro_estado = st.empty() # Indicador de conexión

# --- LÓGICA ---
if encendido:
    p, r = traer_datos(st.session_state.moneda_actual)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
    
    if p:
        evento = "VIGILANDO"
        res_dolar = "$0.00"
        
        # 1. Lógica de Compra
        if not st.session_state.comprado:
            target_visual = p * (1 + (tp_p/100))
            stop_visual = p * (1 - (sl_p/100))
            if r < 35: # Umbral de compra por RSI
                st.session_state.comprado = True
                st.session_state.entrada = p
                st.session_state.target_fijo = target_visual
                st.session_state.stop_fijo = stop_visual
                evento = "🛒 COMPRA ($10)"
        
        # 2. Lógica de Venta
        else:
            target_visual = st.session_state.target_fijo
            stop_visual = st.session_state.stop_fijo
            
            if p >= (st.session_state.target_fijo - 0.0001): 
                dif = (p - st.session_state.entrada) * (monto_trade/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"+${dif:.2f}"
                evento = "💰 VENTA PROFIT"
                st.session_state.comprado = False
            elif p <= (st.session_state.stop_fijo + 0.0001):
                dif = (p - st.session_state.entrada) * (monto_trade/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"${dif:.2f}"
                evento = "📉 VENTA STOP"
                st.session_state.comprado = False
            else:
                evento = f"⏳ HOLD (${st.session_state.entrada:,.2f})"

        # Actualizar Métricas
        m_pre.metric(f"PRECIO {st.session_state.moneda_actual}", f"${p:,.2f}")
        m_rsi.metric("SENSOR RSI", f"{r:.1f}") # RSI en pantalla
        m_bil.metric("BILLETERA USD", f"${st.session_state.saldo:,.2f}")
        m_est.metric("ESTADO", evento)
        
        m_target.metric("VENDER EN (FIXED)", f"${target_visual:,.2f}")
        m_stop.metric("SALIR EN (FIXED)", f"${stop_visual:,.2f}")
        
        # Tabla de Historial
        nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "RSI": f"{r:.1f}", "Ganancia": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(10)
        st.table(st.session_state.log)
        
        # Estado de Conexión (Recuperado)
        cuadro_estado.success(f"🟢 Conexión Activa | {st.session_state.moneda_actual} | {hora} (Arg)")
        
        time.sleep(10)
        st.rerun()
else:
    cuadro_estado.warning("🔴 Bot Apagado - Active el switch para conectar.")
