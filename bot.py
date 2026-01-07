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
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; font-weight: 400 !important; }
    [data-testid="stMetricLabel"] { color: #CCCCCC !important; font-size: 0.9rem !important; }
    .stTable, [data-testid="stTable"] td { color: #FFFFFF !important; font-size: 1rem !important; font-weight: 700 !important; }
    div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False

# --- SIDEBAR AJUSTADA ---
st.sidebar.header("⚙️ Configuración")
moneda_nueva = st.sidebar.selectbox("Seleccionar Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])

# NUEVO: Monto por operación
monto_trade = st.sidebar.number_input("Monto por Trade (USD):", min_value=1.0, max_value=1000.0, value=10.0)

tp_p = st.sidebar.slider("Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Loss %", 0.1, 5.0, 2.0)
encendido = st.sidebar.toggle("🚀 ACTIVAR BOT", value=False)

if st.sidebar.button("🗑️ Limpiar Historial"):
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])
    st.rerun()

# --- DATOS ---
def traer_datos(symbol):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        p = float(res['USD'])
        rsi_sim = 30 + (p % 40)
        return p, rsi_sim
    except: return None, None

# --- PANEL PRINCIPAL ---
st.title(f"🤖 Monitor: {moneda_nueva}")

c1, c2, c3, c4 = st.columns(4)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()
m_est = c4.empty()

st.write(f"### Niveles de Salida (Trade de ${monto_trade})")
c5, c6 = st.columns(2)
m_target = c5.empty()
m_stop = c6.empty()

st.write("---")
cuadro = st.empty()

# --- EJECUCIÓN ---
if encendido:
    p, r = traer_datos(moneda_nueva)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
    
    if p:
        v_target = p * (1 + (tp_p/100))
        v_stop = p * (1 - (sl_p/100))
        
        evento = "VIGILANDO"
        res_dolar = "$0.00"
        
        # Lógica con Monto Específico
        if not st.session_state.comprado and r < 35:
            st.session_state.comprado = True
            st.session_state.entrada = p
            evento = f"🛒 COMPRA (${monto_trade})"
        elif st.session_state.comprado:
            target_real = st.session_state.entrada * (1 + (tp_p/100))
            stop_real = st.session_state.entrada * (1 - (sl_p/100))
            
            if p >= target_real or p <= stop_real:
                # Calculamos la ganancia basada SOLO en el monto del trade
                cantidad_comprada = monto_trade / st.session_state.entrada
                dif = (p - st.session_state.entrada) * cantidad_comprada
                st.session_state.saldo += dif
                res_dolar = f"{'+' if dif > 0 else ''}${dif:.2f}"
                evento = "💰 VENTA PROFIT" if dif > 0 else "📉 VENTA STOP"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLD (DENTRO)"

        m_pre.metric(f"PRECIO {moneda_nueva}", f"${p:,.2f}")
        m_rsi.metric("SENSOR RSI", f"{r:.1f}")
        m_bil.metric("BILLETERA USD", f"${st.session_state.saldo:,.2f}")
        m_est.metric("ESTADO", evento)
        
        m_target.metric("TARGET VENTA", f"${v_target:,.2f}")
        m_stop.metric("STOP LOSS", f"${v_stop:,.2f}")
        
        nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "RSI": f"{r:.1f}", "Ganancia $": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(10)
        st.table(st.session_state.log)
        
        cuadro.success(f"🟢 Activo: {hora} (ARG) | Operando con ${monto_trade}")
        time.sleep(10)
        st.rerun()
else:
    cuadro.warning("🔴 Bot Apagado.")
        
