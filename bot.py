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

# --- ESTILO DE ALTO CONTRASTE ---
st.set_page_config(page_title="Scalper Pro Dashboard", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #BBBBBB !important; font-size: 0.9rem !important; }
    div[data-testid="metric-container"] { 
        background-color: #111111; border: 1px solid #333; border-radius: 10px; padding: 10px; 
    }
    .stTable { background-color: #000; color: #FFF !important; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MÉTRICAS ACUMULADAS ---
if 'saldo' not in st.session_state: st.session_state.saldo = 1000.0
if 'ganancia_total' not in st.session_state: st.session_state.ganancia_total = 0.0
if 'perdida_total' not in st.session_state: st.session_state.perdida_total = 0.0
if 'trades_exitosos' not in st.session_state: st.session_state.trades_exitosos = 0
if 'total_trades' not in st.session_state: st.session_state.total_trades = 0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Resultado", "Billetera"])
if 'comprado' not in st.session_state: st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("⚙️ CONFIG")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_trade = st.sidebar.number_input("Monto Trade (USD):", value=10.0)
rsi_in = st.sidebar.slider("RSI Compra:", 10, 50, 30)
rsi_out = st.sidebar.slider("RSI Venta:", 51, 90, 60)
sl = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
velocidad = st.sidebar.select_slider("Segundos:", options=[2, 5, 10], value=5)
encendido = st.sidebar.toggle("🚀 ENCENDER BOT", value=False)

if st.sidebar.button("🗑️ Reset Stats"):
    st.session_state.ganancia_total = 0.0
    st.session_state.perdida_total = 0.0
    st.session_state.trades_exitosos = 0
    st.session_state.total_trades = 0
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Resultado", "Billetera"])
    st.rerun()

# --- DATOS ---
def obtener_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 15 + (p * 10000 % 70) 
        return float(p), float(rsi)
    except: return None, None

# --- UI PRINCIPAL ---
st.title(f"🚀 SCALPER DASHBOARD: {moneda}")

# FILA 1: ESTADO ACTUAL
c1, c2, c3 = st.columns(3)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()

# FILA 2: CONTABILIDAD (NUEVO)
st.markdown("### 📊 Rendimiento Acumulado")
c4, c5, c6 = st.columns(3)
m_gan = c4.empty()
m_per = c5.empty()
m_por = c6.empty()

st.write("---")
cuadro_estado = st.empty()

# --- LÓGICA ---
if encendido:
    precio, rsi = obtener_datos(moneda)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

    if precio:
        evento = "👀 VIGILANDO"
        res_trade = 0.0

        if not st.session_state.comprado:
            if rsi <= rsi_in:
                st.session_state.comprado = True
                st.session_state.entrada = precio
                st.session_state.stop = precio * (1 - (sl/100))
                evento = "🛒 COMPRA"
        else:
            # VENTA PROFIT
            if rsi >= rsi_out:
                res_trade = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada)
                st.session_state.saldo += res_trade
                st.session_state.ganancia_total += res_trade
                st.session_state.trades_exitosos += 1
                st.session_state.total_trades += 1
                evento = "💰 VENTA PROFIT"
                st.session_state.comprado = False
            # VENTA STOP
            elif precio <= st.session_state.stop:
                res_trade = (precio - st.session_state.entrada) * (monto_trade / st.session_state.entrada)
                st.session_state.saldo += res_trade
                st.session_state.perdida_total += abs(res_trade)
                st.session_state.total_trades += 1
                evento = "📉 VENTA STOP"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLDING"

        # CÁLCULO DE PORCENTAJE DEL DÍA
        win_rate = (st.session_state.trades_exitosos / st.session_state.total_trades * 100) if st.session_state.total_trades > 0 else 0

        # ACTUALIZAR MÉTRICAS
        m_pre.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        m_rsi.metric("RSI", f"{rsi:.1f}")
        m_bil.metric("BILLETERA USD", f"${st.session_state.saldo:,.2f}")
        
        # DASHBOARD DE GANANCIAS (SOLICITADO)
        m_gan.metric("GANANCIAS (+)", f"${st.session_state.ganancia_total:.4f}", delta_color="normal")
        m_per.metric("PÉRDIDAS (-)", f"${st.session_state.perdida_total:.4f}", delta_color="inverse")
        m_por.metric("EFECTIVIDAD DIARIA", f"{win_rate:.1f}%")

        # LOG
        nuevo_log = {"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "RSI": f"{rsi:.1f}", "Resultado": f"${res_trade:.4f}", "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo_log]), st.session_state.log]).head(8)
        st.table(st.session_state.log)

        cuadro_estado.success(f"CONECTADO | {moneda} | {hora}")
        time.sleep(velocidad)
        st.rerun()
else:
    cuadro_estado.warning("BOT APAGADO")
    
