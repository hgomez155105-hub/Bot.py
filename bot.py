import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# ============================
# INICIALIZACIÓN DE SESSION_STATE
# ============================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if 'user_name' not in st.session_state:
    st.session_state.user_name = "Invitado"

# ============================
# FUNCIÓN DE CONEXIÓN A PIONEX
# ============================
def conectar_pionex(api_key, secret_key):
    try:
        exchange = ccxt.pionex({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        exchange.load_markets()
        return exchange
    except Exception as e:
        print("Error conectando a Pionex:", e)
        return None

# ============================
# TOP 20 PARES
# ============================
def obtener_top_20_pionex():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

# ============================
# ACCESO GOOGLE SHEETS
# ============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[
            (df['usuario'].astype(str).str.strip() == str(u).strip()) &
            (df['clave'].astype(str).str.strip() == str(p).strip())
        ]
        return not match.empty
    except:
        return False

# ============================
# CONFIGURACIÓN GENERAL
# ============================
LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

st.set_page_config(
    page_title="BOT T800 - H y G Inovaciones",
    layout="wide",
    page_icon="🤖"
)

# ============================
# TEMA MILITAR ARENA
# ============================
st.markdown(f"""
<style>
.stApp {{
    background-color: #F2E3C6 !important;
    color: #111111 !important;
}}
h1, h2, h3, h4, h5, h6 {{
    color: #3E4F1F !important;
    font-weight: 800 !important;
}}
section[data-testid="stSidebar"] {{
    background-color: #E3D2AC !important;
    color: #111111 !important;
}}
.user-tag {{
    background: #D4C399;
    padding: 5px 15px;
    border-radius: 20px;
    border: 1px solid #3E4F1F;
    color: #111111;
}}
[data-testid="stMetricValue"] {{
    color: #3E4F1F !important;
    font-size: 1.8rem !important;
    font-weight: 900 !important;
}}
.stDataFrame, .stTable {{
    background-color: #FFFFFF !important;
    color: #111111 !important;
}}
</style>
<div style='text-align: center; margin-top: -30px;'>
    <img src="{LOGO_URL}" width="120">
    <h1>BOT T800 – H y G Inovaciones</h1>
</div>
""", unsafe_allow_html=True)

st.sidebar.image(LOGO_URL, width=150)

# ============================
# LOGIN
# ============================
if not st.session_state.autenticado:
    st.markdown("## 🔐 Acceso Táctico T800")

    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("ACCEDER AL SISTEMA"):
        if verificar_acceso(usuario, clave):
            st.session_state.autenticado = True
            st.session_state.user_name = usuario
            st.success("Acceso concedido")
            st.rerun()
        else:
            st.error("Acceso denegado")

    st.stop()

# ============================
# ESTADO INICIAL
# ============================
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'ganancia_total': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'ordenes_malla': [],
        'ultimo_par': "",
        'historial_pnl': [],
        'direccion': 'LONG',
        'ultimo_precio': None,
        'rsi_hist': [],
        'modo_tormenta_activo': False,
        'eventos': [],
        'exchange': None,
        'usdt_balance': None
    })

# ============================
# HEADER
# ============================
c_h1, c_h2 = st.columns([4, 1])

with c_h1:
    st.markdown(
        f"## 🤖 BOT T800 - "
        f"<span class='user-tag'>👤 {st.session_state.user_name}</span>",
        unsafe_allow_html=True
    )

with c_h2:
    st.image(LOGO_URL, width=70)

# ============================
# SIDEBAR
# ============================
with st.sidebar:

    st.subheader("🎯 Objetivo")
    par = st.selectbox("Par (Pionex):", obtener_top_20_pionex())

    if par != st.session_state.ultimo_par:
        st.session_state.update({
            'precios_hist': [],
            'posiciones': [],
            'ordenes_malla': [],
            'rsi_hist': [],
            'ultimo_par': par,
            'eventos': []
        })

    st.divider()

    st.subheader("🔌 Conexión a Pionex")

    api_k = st.text_input("API Key", type="password")
    api_s = st.text_input("Secret Key", type="password")

    if st.button("🔌 Conectar a Pionex", use_container_width=True):
        exchange = conectar_pionex(api_k, api_s)

        if exchange is None:
            st.session_state.exchange = None
            st.session_state.usdt_balance = None
            st.error("❌ No se pudo conectar a Pionex.")
        else:
            try:
                balance = exchange.fetch_balance()
                usdt_balance = balance["total"]["USDT"]

                st.session_state.exchange = exchange
                st.session_state.usdt_balance = usdt_balance

                st.success(f"✅ Conectado | USDT: ${usdt_balance:,.2f}")

            except Exception as e:
                st.session_state.exchange = None
                st.session_state.usdt_balance = None
                st.error(f"❌ Error al leer balance: {e}")

    st.divider()

    st.write("DEBUG EXCHANGE:", st.session_state.exchange)
    st.write("DEBUG USDT_BALANCE:", st.session_state.usdt_balance)

    st.divider()

    st.subheader("⚙️ Configuración de riesgo")

    lev = st.slider("Apalancamiento virtual", 1, 50, 20)
    niveles = st.number_input("Niveles por malla", 1, 50, 7)
    distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05) / 100
    inversion = st.number_input("Inversión total por malla (USDT)", 10.0, 10000.0, 50.0)
    tp_sensible = st.slider("TP por nivel (%)", 0.01, 1.50, 0.05) / 100

    st.divider()

    st.subheader("🎯 RSI")
    rsi_manual = st.slider("RSI Manual (0 = auto)", 0, 100, 0)

    st.divider()

    st.subheader("🧠 Modos T800")
    hedging_on = st.checkbox("🌀 Hedging dinámico", True)
    sniper_on = st.checkbox("🎯 Sniper", True)
    tormenta_on = st.checkbox("🌩️ Tormenta", True)
    cierre_bloque = st.checkbox("🧱 Cierre por bloque", False)
    debug_on = st.checkbox("👀 Debug interno", False)

    st.divider()

    st.subheader("⚡ Saltos de precio")
    salto_rapido = st.slider("Salto rápido (%)", 0.1, 2.0, 0.5) / 100
    sleep_normal = st.slider("Delay normal (seg)", 0.2, 3.0, 0.7)
    sleep_rapido = st.slider("Delay rápido (seg)", 0.03, 0.5, 0.12)

    st.divider()

    if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
        st.session_state.update({
            'posiciones': [],
            'ordenes_malla': [],
            'modo_tormenta_activo': False,
            'eventos': []
        })
        st.rerun()

# ============================
# FUNCIONES TÉCNICAS
# ============================
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return None
    dif = np.diff(precios)
    ganancias = np.where(dif > 0, dif, 0)
    perdidas = np.where(dif < 0, -dif, 0)
    media_gan = pd.Series(ganancias).rolling(periodo).mean().iloc[-1]
    media_per = pd.Series(perdidas).rolling(periodo).mean().iloc[-1]
    if media_per == 0:
        return 100
    rs = media_gan / media_per
    return 100 - (100 / (1 + rs))

# ============================
# TENDENCIA HÍBRIDA (RSI + PENDIENTE)
# ============================
def obtener_tendencia(precios, rsi):
    if len(precios) < 5 or rsi is None:
        return "LONG"
    slope = precios[-1] - precios[-5]
    if slope > 0 and rsi < 70:
        return "LONG"
    if slope < 0 and rsi > 30:
        return "SHORT"
    return "LONG"

# ============================
# BOTÓN MANUAL – EJECUTAR CICLO
# ============================
st.markdown("## ▶️ Ejecutar T800")

if st.button("Ejecutar T800", use_container_width=True):

    # Conexión obligatoria
    if st.session_state.exchange is None:
        st.error("❌ No hay conexión a Pionex. Conectá primero.")
        st.stop()

    exchange = st.session_state.exchange

    # PRECIO REAL
    ticker = exchange.fetch_ticker(par.replace("/", ""))
    precio_act = float(ticker["last"])

    # CAMBIO DE PRECIO
    precio_anterior = st.session_state.ultimo_precio
    st.session_state.ultimo_precio = precio_act

    if precio_anterior:
        cambio_pct = abs(precio_act - precio_anterior) / precio_anterior
    else:
        cambio_pct = 0

    # MODO TORMENTA
    if tormenta_on and cambio_pct >= salto_rapido:
        st.session_state.modo_tormenta_activo = True
    else:
        st.session_state.modo_tormenta_activo = False

    # HISTORIAL
    st.session_state.precios_hist.append(precio_act)
    if len(st.session_state.precios_hist) > 300:
        st.session_state.precios_hist.pop(0)

    # RSI
    rsi_real = calcular_rsi(st.session_state.precios_hist)
    rsi_use = rsi_manual if rsi_manual != 0 else rsi_real
    st.session_state.rsi_hist.append(rsi_use)

    # TENDENCIA
    tendencia_calc = obtener_tendencia(st.session_state.precios_hist, rsi_use)
    st.session_state.direccion = tendencia_calc

    # ============================
    # ARMADO DE MALLA
    # ============================
    direcciones_malla = {o['dir'] for o in st.session_state.ordenes_malla}

    if hedging_on:
        if tendencia_calc not in direcciones_malla:
            monto_nivel = inversion / niveles
            for i in range(niveles):
                factor = 1 - (i * distancia) if tendencia_calc == "LONG" else 1 + (i * distancia)
                st.session_state.ordenes_malla.append({
                    'id': len(st.session_state.ordenes_malla) + 1,
                    'precio': round(precio_act * factor, 4),
                    'monto': round(monto_nivel, 2),
                    'estado': 'PENDIENTE',
                    'dir': tendencia_calc
                })
    else:
        st.session_state.ordenes_malla = [
            o for o in st.session_state.ordenes_malla if o['dir'] == tendencia_calc
        ]

    # ============================
    # EJECUCIÓN DE ÓRDENES
    # ============================
    nuevas_ordenes = []

    for o in st.session_state.ordenes_malla:
        if o['estado'] != 'PENDIENTE':
            nuevas_ordenes.append(o)
            continue

        dir_o = o['dir']
        hit = precio_act <= o['precio'] if dir_o == "LONG" else precio_act >= o['precio']

        # SNIPER
        if sniper_on and precio_anterior:
            micro_pico = abs(precio_act - precio_anterior) / precio_anterior
            sensibilidad = max(0.0005, cambio_pct * 0.6)
            if dir_o == "LONG":
                hit = hit and (rsi_use < 80 and micro_pico >= sensibilidad)
            else:
                hit = hit and (rsi_use > 20 and micro_pico >= sensibilidad)

        if hit:
            # ORDEN REAL
            side = 'buy' if dir_o == "LONG" else 'sell'
            try:
                exchange.create_market_order(par, side, o['monto'] / precio_act)
            except:
                pass

            # ORDEN DEMO
            st.session_state.saldo_demo -= o['monto']
            o['estado'] = 'EJECUTADA'

            tp_factor = tp_sensible * (0.7 if st.session_state.modo_tormenta_activo else 1.0)
            tp_price = precio_act * (1 + tp_factor) if dir_o == "LONG" else precio_act * (1 - tp_factor)

            st.session_state.posiciones.append({
                'id_orden': o['id'],
                'entrada': precio_act,
                'monto': o['monto'],
                'tp_precio': tp_price,
                'dir': dir_o
            })

            st.session_state.eventos.append({
                'tipo': 'APERTURA',
                'precio': precio_act,
                'dir': dir_o,
                'id_orden': o['id'],
                'ts': datetime.now().strftime("%H:%M:%S")
            })

        nuevas_ordenes.append(o)

    st.session_state.ordenes_malla = nuevas_ordenes

    # ============================
    # GESTIÓN DE POSICIONES
    # ============================
    nuevas_posiciones = []

    for pos in st.session_state.posiciones:
        entrada = pos['entrada']
        monto = pos['monto']
        tp_price = pos['tp_precio']
        dir_pos = pos['dir']

        if dir_pos == "LONG":
            tp_hit = precio_act >= tp_price
            retorno = (precio_act / entrada) - 1
        else:
            tp_hit = precio_act <= tp_price
            retorno = 1 - (precio_act / entrada)

        pnl_nivel = retorno * monto * lev

        tendencia_contra = (
            (dir_pos == "LONG" and tendencia_calc == "SHORT") or
            (dir_pos == "SHORT" and tendencia_calc == "LONG")
        )

        escape_ganancia = pnl_nivel > 0 and tendencia_contra

        if pnl_nivel > 0 and (tp_hit or escape_ganancia):

            side_close = 'sell' if dir_pos == "LONG" else 'buy'
            try:
                exchange.create_market_order(par, side_close, monto / precio_act)
            except:
                pass

            st.session_state.saldo_demo += (monto + pnl_nivel)
            st.session_state.ganancia_total += pnl_nivel

            st.session_state.historial_pnl.append({
                'Fecha': datetime.now().strftime("%H:%M:%S"),
                'Tipo': f"{dir_pos} - Nivel {pos['id_orden']}",
                'Ganancia': round(pnl_nivel, 4)
            })

            st.session_state.eventos.append({
                'tipo': 'CIERRE',
                'precio': precio_act,
                'dir': dir_pos,
                'id_orden': pos['id_orden'],
                'ts': datetime.now().strftime("%H:%M:%S")
