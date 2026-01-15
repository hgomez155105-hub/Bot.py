import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# ============================
# LOGO
# ============================
LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# ============================
# CONFIGURACIÓN DE ACCESO (GOOGLE SHEETS)
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
# CONFIGURACIÓN PÁGINA
# ============================
st.set_page_config(
    page_title="T800 – H y G Inovaciones",
    layout="wide",
    page_icon="🤖"
)

# ============================
# ESTILO VISUAL OSCURO
# ============================
st.markdown(f"""
<style>
.stApp {{
    background-color: #0B0E11 !important;
}}
.user-tag {{
    background: #1E2329;
    padding: 5px 15px;
    border-radius: 20px;
    border: 1px solid #F0B90B;
    color: white;
}}
[data-testid="stMetricValue"] {{
    color: #F0B90B !important;
    font-size: 1.8rem !important;
}}
h1, h2, h3 {{
    color: white !important;
}}
</style>
<div style='text-align: center; margin-top: -30px;'>
    <img src="{LOGO_URL}" width="120">
    <h1 style='color: white;'>T800 – H y G Inovaciones</h1>
</div>
""", unsafe_allow_html=True)

st.sidebar.image(LOGO_URL, width=150)

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
# TOP 20 PARES (BINANCE → PIONEX)
# ============================
def obtener_top_20_pionex():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df = pd.DataFrame(res)
        df = df[df['symbol'].str.endswith("USDT")]
        df['quoteVolume'] = df['quoteVolume'].astype(float)
        top = df.sort_values("quoteVolume", ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top['symbol']]
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# ============================
# LOGIN
# ============================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>T800 – Acceso</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("Acceso denegado.")
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
        'exchange': None,
        'usdt_balance': None
    })

# ============================
# HEADER
# ============================
c1, c2 = st.columns([4, 1])
c1.markdown(
    f"## 🤖 T800 – "
    f"<span class='user-tag'>👤 {st.session_state.user_name}</span>",
    unsafe_allow_html=True
)
c2.image(LOGO_URL, width=70)

# ============================
# SIDEBAR
# ============================
with st.sidebar:

    st.subheader("🎯 Par de Trading")
    par = st.selectbox("Par (Pionex):", obtener_top_20_pionex())

    if par != st.session_state.ultimo_par:
        st.session_state.update({
            'precios_hist': [],
            'posiciones': [],
            'ordenes_malla': [],
            'rsi_hist': [],
            'ultimo_par': par
        })

    st.divider()

    st.subheader("🔌 Conexión a Pionex")
    api_k = st.text_input("API Key", type="password")
    api_s = st.text_input("Secret Key", type="password")

    if st.button("🔌 Conectar a Pionex", use_container_width=True):
        ex = conectar_pionex(api_k, api_s)
        if ex is None:
            st.session_state.exchange = None
            st.error("❌ No se pudo conectar a Pionex.")
        else:
            try:
                bal = ex.fetch_balance()
                st.session_state.exchange = ex
                st.session_state.usdt_balance = bal["total"]["USDT"]
                st.success(f"✅ Conectado | USDT: {st.session_state.usdt_balance}")
            except:
                st.session_state.exchange = None
                st.error("❌ Error leyendo balance.")

    st.divider()

    st.subheader("⚙️ Configuración de riesgo")
    lev = st.slider("Apalancamiento", 1, 50, 20)
    niveles = st.number_input("Niveles por malla", 1, 50, 7)
    distancia = st.slider("Distancia malla (%)", 0.01, 1.0, 0.05) / 100
    inversion = st.number_input("Inversión total (USDT)", 10.0, 10000.0, 50.0)
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
    debug_on = st.checkbox("👀 Debug", False)

    st.divider()

    st.subheader("⚡ Saltos")
    salto_rapido = st.slider("Salto rápido (%)", 0.1, 2.0, 0.5) / 100

    if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
        st.session_state.posiciones = []
        st.session_state.ordenes_malla = []
        st.session_state.eventos = []
        st.rerun()
        # ============================
# FUNCIONES TÉCNICAS
# ============================
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return 50
    dif = np.diff(precios)
    ganancias = np.where(dif > 0, dif, 0)
    perdidas = np.where(dif < 0, -dif, 0)
    avg_gain = pd.Series(ganancias).rolling(periodo).mean().iloc[-1]
    avg_loss = pd.Series(perdidas).rolling(periodo).mean().iloc[-1]
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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

    # ❌ SI NO HAY CONEXIÓN → NO ARRANCA
    if st.session_state.exchange is None:
        st.error("❌ No hay conexión a Pionex. Conectá primero.")
        st.stop()

    exchange = st.session_state.exchange

    # PRECIO REAL DE PIONEX (SIN FALLBACK)
    try:
        ticker = exchange.fetch_ticker(par.replace("/", ""))
        precio_act = float(ticker["last"])
    except:
        st.error("❌ Error obteniendo precio real de Pionex.")
        st.stop()

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
        if sniper_on and st.session_state.ultimo_precio:
            micro_pico = abs(precio_act - st.session_state.ultimo_precio) / st.session_state.ultimo_precio
            sensibilidad = max(0.0005, micro_pico * 0.6)
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

        else:
            nuevas_posiciones.append(pos)

    st.session_state.posiciones = nuevas_posiciones
    # ============================
# GRÁFICO TÁCTICO T800
# ============================
st.markdown("### 📈 Gráfico Táctico T800 (Precio, RSI, Niveles, TP, Ejecuciones)")

precios = st.session_state.precios_hist

if len(precios) > 1:
    fig = go.Figure()

    # Precio
    fig.add_trace(go.Scatter(
        y=precios,
        name="Precio",
        line=dict(color="#F0B90B", width=3)
    ))

    # RSI
    if st.session_state.rsi_hist:
        fig.add_trace(go.Scatter(
            y=st.session_state.rsi_hist,
            name="RSI",
            line=dict(color="magenta", width=2, dash="dot"),
            yaxis="y2"
        ))

    # Líneas de malla
    if st.session_state.ordenes_malla:
        for o in st.session_state.ordenes_malla:
            color = "gray" if o["estado"] == "PENDIENTE" else "#F39C12"
            fig.add_hline(
                y=o["precio"],
                line=dict(color=color, width=1, dash="dot"),
                opacity=0.3
            )

    # Entradas y TP
    if st.session_state.posiciones:
        x_idx = [len(precios) - 1] * len(st.session_state.posiciones)

        fig.add_trace(go.Scatter(
            x=x_idx,
            y=[p["entrada"] for p in st.session_state.posiciones],
            mode="markers",
            name="Entradas",
            marker=dict(color="cyan", size=9, symbol="triangle-up")
        ))

        fig.add_trace(go.Scatter(
            x=x_idx,
            y=[p["tp_precio"] for p in st.session_state.posiciones],
            mode="markers",
            name="TP",
            marker=dict(color="lime", size=8, symbol="x")
        ))

    fig.update_layout(
        height=450,
        template="plotly_dark",
        margin=dict(l=0, r=0, b=0, t=10),
        yaxis=dict(title="Precio"),
        yaxis2=dict(
            title="RSI",
            overlaying="y",
            side="right",
            range=[0, 100]
        )
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Esperando datos de precio para dibujar el gráfico...")

# ============================
# TABLAS
# ============================

st.subheader("📋 Malla de Operación (Órdenes abiertas)")
if st.session_state.ordenes_malla:
    st.dataframe(st.session_state.ordenes_malla, use_container_width=True)
else:
    st.info("Sin órdenes en malla por el momento.")

st.subheader("📌 Posiciones abiertas")
if st.session_state.posiciones:
    st.dataframe(st.session_state.posiciones, use_container_width=True)
else:
    st.info("Sin posiciones abiertas.")

st.subheader("📜 Historial de PnL")
if st.session_state.historial_pnl:
    st.dataframe(st.session_state.historial_pnl, use_container_width=True)
else:
    st.info("Sin operaciones cerradas aún.")
