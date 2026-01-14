import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# ============================
# CONFIGURACIÓN GENERAL
# ============================
st.set_page_config(page_title="BOT T800", layout="wide", page_icon="🤖")

# ============================
# TEMA MILITAR CLARO (ARENA)
# ============================
st.markdown("""
<style>
.stApp {
    background-color: #F2E9D8 !important; /* Arena claro */
    color: #000000 !important;
}

/* Títulos */
h1, h2, h3, h4, h5, h6 {
    color: #556B2F !important; /* Verde oliva */
    font-weight: 800 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #E8DFC8 !important; /* Arena más oscuro */
    color: #000000 !important;
}

/* Inputs */
input, textarea, select {
    background-color: #FFF !important;
    color: #000 !important;
}

/* Botones */
button[kind="primary"] {
    background-color: #556B2F !important;
    color: white !important;
    border: 2px solid #3E4F1F !important;
    font-weight: 700 !important;
}

/* Métricas */
[data-testid="stMetricValue"] {
    color: #556B2F !important;
    font-size: 1.8rem !important;
    font-weight: 900 !important;
}

[data-testid="stMetricDelta"] {
    color: #000 !important;
}

/* Tablas */
.stDataFrame, .stTable {
    background-color: #FFF !important;
    color: #000 !important;
}
</style>
""", unsafe_allow_html=True)

LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# ============================
# FUNCIONES
# ============================
def conectar_pionex(api_key, secret_key):
    try:
        exchange = ccxt.pionex({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True
        })
        return exchange
    except:
        return None

def obtener_top_20_pionex():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df = pd.DataFrame(res)
        df = df[df["symbol"].str.endswith("USDT")]
        df["quoteVolume"] = df["quoteVolume"].astype(float)
        top = df.sort_values("quoteVolume", ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top["symbol"]]
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def obtener_tendencia(precios):
    if len(precios) < 10:
        return "LONG"
    ema = np.mean(precios[-10:])
    return "LONG" if precios[-1] >= ema else "SHORT"

# ============================
# LOGIN
# ============================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align:center;'>BOT T800</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            st.session_state.autenticado = True
            st.session_state.user_name = u
            st.rerun()
else:

    # ============================
    # ESTADO INICIAL
    # ============================
    if "saldo_demo" not in st.session_state:
        st.session_state.saldo_demo = 1000.0
        st.session_state.ganancia_total = 0.0
        st.session_state.posiciones = []
        st.session_state.precios_hist = []
        st.session_state.ordenes_malla = []
        st.session_state.ultimo_par = ""
        st.session_state.historial_pnl = []
        st.session_state.direccion = "LONG"
        st.session_state.max_pnl_alcanzado = 0.0

    # ============================
    # HEADER
    # ============================
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"## 🤖 BOT T800 — 👤 {st.session_state.user_name}")
    c2.image(LOGO_URL, width=70)

    # ============================
    # SIDEBAR
    # ============================
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Objetivo Pionex:", obtener_top_20_pionex())

        if par != st.session_state.ultimo_par:
            st.session_state.ultimo_par = par
            st.session_state.precios_hist = []
            st.session_state.posiciones = []
            st.session_state.ordenes_malla = []
            st.session_state.max_pnl_alcanzado = 0.0

        st.subheader("🔑 Conexión Exchange")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")

        st.subheader("⚙️ Configuración base")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Cantidad de Niveles", 1, 50, 10)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.2) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        tp_sensible = st.slider("Profit Objetivo base (%)", 0.005, 1.0, 0.1, format="%.3f") / 100

        sniper = st.checkbox("🎯 Modo Sniper", True)
        hedging = st.checkbox("🌀 Hedging dinámico", True)
        tormenta = st.checkbox("🌩️ Modo Tormenta", True)

        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.posiciones = []
            st.session_state.ordenes_malla = []
            st.session_state.max_pnl_alcanzado = 0.0
            st.rerun()

    # ============================
    # AJUSTES
    # ============================
    tp_objetivo = tp_sensible
    distancia_malla = distancia
    sleep_time = 1.0

    if sniper:
        tp_objetivo *= 0.5
    if tormenta:
        distancia_malla *= 0.7
        sleep_time = 0.7

    # ============================
    # MOTOR T800
    # ============================
    bot_on = st.toggle("🚀 ACTIVAR BOT T800")

    if bot_on:
        try:
            exchange = None
            if entorno == "🟡 MODO REAL" and api_k and api_s:
                exchange = conectar_pionex(api_k, api_s)

            base_symbol = par.split("/")[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={base_symbol}&tsyms=USD").json()
            precio_act = float(res["USD"])

            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 200:
                st.session_state.precios_hist.pop(0)

            rsi_val = calcular_rsi(st.session_state.precios_hist)
            tendencia = obtener_tendencia(st.session_state.precios_hist)

            # ============================
            # MÉTRICAS
            # ============================
            c1, c2, c3 = st.columns(3)

            c1.metric(f"Precio ({tendencia})", f"${precio_act:,.4f}", f"RSI {rsi_val:.1f}")

            try:
                if exchange:
                    balance = exchange.fetch_balance()
                    usdt_balance = balance["total"]["USDT"]
                    c2.metric("💰 Wallet REAL", f"${usdt_balance:,.2f}")
                else:
                    c2.metric("💰 Wallet DEMO", f"${st.session_state.saldo_demo:,.2f}")
            except:
                c2.metric("💰 Wallet REAL", "Error")

            c3.metric("PNL Total", f"${st.session_state.ganancia_total:,.2f}")

            # ============================
            # (RESTO DEL MOTOR: MALLA, EJECUCIONES, GRÁFICOS…)
            # ============================

            st.info("Motor funcionando… (acá seguiría tu lógica completa)")

            time.sleep(sleep_time)
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(3)
            st.rerun()

    else:
        st.info("Bot T800 apagado.")
