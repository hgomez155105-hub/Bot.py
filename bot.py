import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

LOGO_URL = "https://i.imgur.com/7ZkEw2k.png"
TELEGRAM_URL = "https://t.me/TU_TELEGRAM"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

st.set_page_config(
    page_title="Bot T800",
    layout="wide",
    page_icon=LOGO_URL
)

# ============================================================
# ESTILO MILITAR
# ============================================================

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #2d3a26, #0a0c08 55%) !important;
    color: white !important;
    font-family: monospace;
}
[data-testid="stSidebar"] > div:first-child {
    background-color: #050605 !important;
    border-right: 1px solid #3a4a30;
}
h1, h2, h3, h4, h5, h6, label, p, span {
    color: #f5f5f5 !important;
}
.stMetric, [data-testid="stMetricValue"] {
    color: #d7e5d0 !important;
}
.stButton>button {
    background-color: #3A4A2C !important;
    color: white !important;
    border-radius: 8px;
    border: 1px solid #7e9461;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #556644 !important;
    border-color: #c1d38e;
}
input, textarea {
    background-color: #0D0F0A !important;
    color: white !important;
    border-radius: 6px;
    border: 1px solid #3a4a30;
}
.t800-card {
    border-radius: 10px;
    padding: 12px 16px;
    background: linear-gradient(135deg, #11140f, #22291b);
    border: 1px solid #445338;
    box-shadow: 0 0 12px rgba(0,0,0,0.7);
}
.t800-title {
    font-size: 1.1rem;
    color: #dfe9d7;
    border-bottom: 1px dashed #4e6140;
    padding-bottom: 4px;
    margin-bottom: 8px;
}
.glow {
    animation: glowPulse 1.5s ease-in-out infinite alternate;
}
@keyframes glowPulse {
    from { text-shadow: 0 0 4px #a3ff73; }
    to   { text-shadow: 0 0 12px #e4ff99; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# LOGIN
# ============================================================

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[
            (df["usuario"].astype(str).str.strip() == str(u).strip()) &
            (df["clave"].astype(str).str.strip() == str(p).strip())
        ]
        return not match.empty
    except:
        return False

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.image(LOGO_URL, width=180)
        st.markdown("<h1 class='glow'>Bot T800</h1>", unsafe_allow_html=True)
        st.markdown("<p>Acceso táctico restringido</p>", unsafe_allow_html=True)

        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")

        if st.button("INGRESAR", use_container_width=True):
            if verificar_acceso(usuario, clave):
                st.session_state.autenticado = True
                st.session_state.user = usuario
                st.rerun()
            else:
                st.error("Acceso denegado. Verifique su base de datos.")

        st.markdown(
            f"<p style='text-align:center; margin-top:30px;'>"
            f"<a href='{TELEGRAM_URL}' style='color:#9FB89F; text-decoration:none;'>📡 Contacto Telegram</a>"
            f"</p>",
            unsafe_allow_html=True
        )
    st.stop()

# ============================================================
# ESTADO INICIAL
# ============================================================

if "estado" not in st.session_state:
    st.session_state.estado = {
        "saldo_demo": 1000.0,
        "ganancia_total": 0.0,
        "posiciones": [],
        "ordenes_malla": [],
        "precios": [],
        "rsi_hist": [],
        "ultimo_precio": None,
        "direccion": "LONG",
        "modo_tormenta": False,
        "historial_pnl": []
    }

# ============================================================
# FUNCIONES TÉCNICAS
# ============================================================

def conectar_binance(api, sec):
    try:
        return ccxt.binance({
            "apiKey": api,
            "secret": sec,
            "enableRateLimit": True,
            "options": {"defaultType": "future"}
        })
    except:
        return None

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

def obtener_tendencia(precios, rsi):
    if len(precios) < 10:
        return st.session_state.estado["direccion"]
    ema = np.mean(precios[-10:])
    precio = precios[-1]
    if precio >= ema and rsi <= 70:
        return "LONG"
    elif precio < ema and rsi >= 25:
        return "SHORT"
    return st.session_state.estado["direccion"]

def sniper_disparo(dir_o, precio_act, precio_ant, rsi_use, volatilidad):
    if precio_ant is None or precio_ant <= 0:
        return False
    micro_pico = abs(precio_act - precio_ant) / precio_ant
    sensibilidad = max(0.0005, volatilidad * 0.6)
    rsi_alto = 85
    rsi_bajo = 15
    if dir_o == "LONG":
        return (rsi_use < rsi_alto) and (micro_pico >= sensibilidad)
    else:
        return (rsi_use > rsi_bajo) and (micro_pico >= sensibilidad)
# ============================================================
# HEADER
# ============================================================

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(
        f"<div class='t800-card'>"
        f"<div class='t800-title'>👁️ Bot T800 – Operador</div>"
        f"<p>👤 {st.session_state.user}</p>"
        f"<p>El algoritmo está listo para operar en modo táctico.</p>"
        f"</div>",
        unsafe_allow_html=True
    )
with col_h2:
    st.image(LOGO_URL, width=80)

st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.image(LOGO_URL, width=120)
    st.markdown("### 🎯 Objetivo")

    par = st.selectbox("Par:", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"])

    st.markdown("### 🔑 Conexión Exchange")
    entorno = st.radio("Entorno:", ["DEMO", "REAL"])
    api = st.text_input("API Key", type="password")
    sec = st.text_input("Secret Key", type="password")

    st.markdown("### ⚙️ Parámetros de riesgo")
    lev = st.slider("Apalancamiento", 1, 50, 22)
    niveles = st.slider("Niveles por malla", 1, 25, 7)
    distancia = st.slider("Distancia malla (%)", 0.01, 1.0, 0.05, format="%.3f") / 100
    inversion = st.number_input("Inversión total por malla (USDT)", 10.0, 5000.0, 10.0)
    tp = st.slider("TP por nivel (%)", 0.01, 1.5, 0.03, format="%.3f") / 100

    st.markdown("### 🎯 RSI")
    rsi_manual = st.slider("RSI Manual (0 = auto)", 0, 100, 0)

    st.markdown("### 🧠 Modos tácticos")
    sniper = st.checkbox("🎯 Modo Sniper", True)
    hedging = st.checkbox("🌀 Hedging dinámico", True)
    tormenta = st.checkbox("🌩️ Modo Tormenta", True)
    cierre_bloque = st.checkbox("🧱 Cierre por bloque si PnL total > 0", False)
    debug = st.checkbox("👀 Debug interno por nivel", False)

    st.markdown("### ⚡ Respuesta a saltos de precio")
    salto_rapido = st.slider("Salto precio modo rápido (%)", 0.1, 2.0, 0.5, format="%.2f") / 100
    sleep_normal = st.slider("Delay normal (seg)", 0.2, 3.0, 0.7)
    sleep_rapido = st.slider("Delay rápido (seg)", 0.03, 0.5, 0.12)
    
    st.markdown("### 📡 Gráfico")
grafico_tiempo_real = st.checkbox("Gráfico en tiempo real", False)
    st.markdown("---")
    if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
        st.session_state.estado["posiciones"] = []
        st.session_state.estado["ordenes_malla"] = []
        st.session_state.estado["modo_tormenta"] = False
        st.warning("Botón de pánico activado. Posiciones y mallas limpiadas.")
        st.experimental_rerun()

    st.markdown("---")
    if st.button("🔒 Cerrar sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.experimental_rerun()

# ============================================================
# MOTOR T800
# ============================================================

bot_on = st.toggle("🚀 ACTIVAR BOT T800")

exchange = None
if entorno == "REAL" and api and sec:
    exchange = conectar_binance(api, sec)

precio_actual = None
rsi_use = 50
tendencia = st.session_state.estado["direccion"]
volatilidad = 0.0

# ============================================================
# PRECIO SIEMPRE ACTUALIZADO — FUERA DEL IF
# ============================================================

try:
    r = requests.get(
        f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD"
    )
    data = r.json()
    precio_actual = float(data["USD"])
except Exception as e:
    st.error(f"No se pudo obtener el precio: {e}")
    precio_actual = None
    
# Guardar precio SIEMPRE
if precio_actual:
    st.session_state.estado["precios"].append(precio_actual)
    if len(st.session_state.estado["precios"]) > 500:
        st.session_state.estado["precios"].pop(0)
        
# ============================================================
# MOTOR TÁCTICO — SOLO SI EL BOT ESTÁ ACTIVADO
# ============================================================

if bot_on:

    # Guardar precio en historial (CORRECCIÓN CLAVE)
    st.session_state.estado["precios"].append(precio_actual)
    if len(st.session_state.estado["precios"]) > 500:
        st.session_state.estado["precios"].pop(0)

    precios = st.session_state.estado["precios"]

    # 2) VOLATILIDAD / TORMENTA
    precio_ant = st.session_state.estado["ultimo_precio"]
    st.session_state.estado["ultimo_precio"] = precio_actual

    if precio_ant is not None and precio_ant > 0:
        volatilidad = abs(precio_actual - precio_ant) / precio_ant
    else:
        volatilidad = 0.0

    if tormenta and volatilidad >= salto_rapido:
        st.session_state.estado["modo_tormenta"] = True
        delay = sleep_rapido
    else:
        st.session_state.estado["modo_tormenta"] = False
        delay = sleep_normal

    # 3) RSI Y TENDENCIA (CORREGIDO)
    rsi_real = calcular_rsi(precios)
    rsi_use = rsi_manual if rsi_manual != 0 else rsi_real

    rsi_hist = st.session_state.estado["rsi_hist"]
    rsi_hist.append(rsi_use)
    if len(rsi_hist) > 500:
        rsi_hist.pop(0)

    tendencia = obtener_tendencia(precios, rsi_use)
    st.session_state.estado["direccion"] = tendencia
    # 4) ARMADO/ACTUALIZACIÓN DE MALLAS
    ordenes = st.session_state.estado["ordenes_malla"]
    dirs_existentes = {o["dir"] for o in ordenes} if ordenes else set()

    def crear_malla(direccion_ref):
        monto_nivel = inversion / max(niveles, 1)
        for i in range(niveles):
            if direccion_ref == "LONG":
                factor = 1 - (i * distancia)
            else:
                factor = 1 + (i * distancia)
            ordenes.append({
                "id": len(ordenes) + 1,
                "precio": round(precio_actual * factor, 4),
                "monto": round(monto_nivel, 2),
                "estado": "PENDIENTE",
                "dir": direccion_ref
            })

    if hedging:
        if tendencia not in dirs_existentes:
            crear_malla(tendencia)
    else:
        ordenes[:] = [o for o in ordenes if o["dir"] == tendencia]
        if tendencia not in dirs_existentes:
            crear_malla(tendencia)

    # 5) EJECUCIÓN DE ÓRDENES DE MALLA
    posiciones = st.session_state.estado["posiciones"]
    for o in ordenes:
        if o["estado"] != "PENDIENTE":
            continue

        dir_o = o["dir"]
        hit_basico = (precio_actual <= o["precio"]) if dir_o == "LONG" else (precio_actual >= o["precio"])
        hit = hit_basico

        if sniper:
            sniper_hit = sniper_disparo(dir_o, precio_actual, precio_ant, rsi_use, volatilidad)
            hit = hit_basico and sniper_hit

        if hit:
            entrada_real = precio_actual
            tp_factor = tp * (0.7 if st.session_state.estado["modo_tormenta"] else 1.0)
            if dir_o == "LONG":
                tp_price = entrada_real * (1 + tp_factor)
            else:
                tp_price = entrada_real * (1 - tp_factor)

            posiciones.append({
                "id_orden": o["id"],
                "entrada": entrada_real,
                "monto": o["monto"],
                "tp_precio": tp_price,
                "dir": dir_o
            })
            o["estado"] = "EJECUTADA"

    # 6) GESTIÓN DE POSICIONES
    nuevas_posiciones = []
    pnl_niveles = []

    for pos in posiciones:
        entrada = pos["entrada"]
        monto = pos["monto"]
        tp_precio = pos["tp_precio"]
        dir_pos = pos["dir"]

        if dir_pos == "LONG":
            tp_hit = precio_actual >= tp_precio
            retorno = (precio_actual / entrada) - 1
        else:
            tp_hit = precio_actual <= tp_precio
            retorno = 1 - (precio_actual / entrada)

        pnl_nivel = retorno * monto * lev
        pnl_niveles.append(pnl_nivel)

        tendencia_contra = (
            (dir_pos == "LONG" and tendencia == "SHORT") or
            (dir_pos == "SHORT" and tendencia == "LONG")
        )
        escape_ganancia = pnl_nivel > 0 and tendencia_contra

        if debug:
            st.write(
                f"Nivel {pos['id_orden']} | Dir_pos: {dir_pos} | Tend: {tendencia} | "
                f"Entrada: {entrada:.4f} | TP: {tp_precio:.4f} | "
                f"Precio: {precio_actual:.4f} | Retorno: {retorno*100:.4f}% | "
                f"PnL: {pnl_nivel:.4f} | TP_hit: {tp_hit} | Escape: {escape_ganancia} | "
                f"RSI: {rsi_use:.1f} | Tormenta: {st.session_state.estado['modo_tormenta']}"
            )

        if pnl_nivel > 0 and (tp_hit or escape_ganancia):
            if exchange:
                side_close = "sell" if dir_pos == "LONG" else "buy"
                try:
                    exchange.create_market_order(par, side_close, monto / precio_actual)
                except Exception as ex:
                    st.warning(f"Cierre real fallido (nivel): {ex}")

            st.session_state.estado["saldo_demo"] += (monto + pnl_nivel)
            st.session_state.estado["ganancia_total"] += pnl_nivel
            st.session_state.estado["historial_pnl"].append({
                "Fecha": datetime.now().strftime("%H:%M:%S"),
                "Tipo": f"{dir_pos} - Nivel {pos['id_orden']}",
                "Ganancia": round(pnl_nivel, 4)
            })

            for o in ordenes:
                if o["id"] == pos["id_orden"] and o["dir"] == dir_pos:
                    o["estado"] = "PENDIENTE"
                    break
        else:
            nuevas_posiciones.append(pos)

    st.session_state.estado["posiciones"] = nuevas_posiciones

    # 7) CIERRE POR BLOQUE
    if cierre_bloque and st.session_state.estado["posiciones"]:
        pnl_total_bloque = 0.0
        for pos in st.session_state.estado["posiciones"]:
            entrada = pos["entrada"]
            monto = pos["monto"]
            dir_pos = pos["dir"]
            if dir_pos == "LONG":
                retorno_b = (precio_actual / entrada) - 1
            else:
                retorno_b = 1 - (precio_actual / entrada)
            pnl_total_bloque += retorno_b * monto * lev

        if pnl_total_bloque > 0:
            for pos in st.session_state.estado["posiciones"]:
                entrada = pos["entrada"]
                monto = pos["monto"]
                dir_pos = pos["dir"]
                if dir_pos == "LONG":
                    retorno_b = (precio_actual / entrada) - 1
                    side_close = "sell"
                else:
                    retorno_b = 1 - (precio_actual / entrada)
                    side_close = "buy"
                pnl_nivel_b = retorno_b * monto * lev

                if exchange:
                    try:
                        exchange.create_market_order(par, side_close, monto / precio_actual)
                    except Exception as ex:
                        st.warning(f"Cierre real fallido (bloque): {ex}")

                st.session_state.estado["saldo_demo"] += (monto + pnl_nivel_b)
                st.session_state.estado["ganancia_total"] += pnl_nivel_b
                st.session_state.estado["historial_pnl"].append({
                    "Fecha": datetime.now().strftime("%H:%M:%S"),
                    "Tipo": f"{dir_pos} - BLOQUE",
                    "Ganancia": round(pnl_nivel_b, 4)
                })

            st.session_state.estado["posiciones"] = []
            st.session_state.estado["ordenes_malla"] = []

# ============================================================
# PANELES TÁCTICOS
# ============================================================

col_m1, col_m2, col_m3 = st.columns(3)
saldo = st.session_state.estado["saldo_demo"]
gan_total = st.session_state.estado["ganancia_total"]

with col_m1:
    st.metric("Wallet DEMO", f"${saldo:,.2f}")
with col_m2:
    st.metric("PNL Total", f"${gan_total:,.2f}")
with col_m3:
    if precio_actual is not None:
        st.metric(f"Precio {par}", f"${precio_actual:,.4f}")
    else:
        st.metric(f"Precio {par}", "–")

st.markdown("")

c_info1, c_info2 = st.columns([2, 1])
with c_info1:
    st.markdown(
        "<div class='t800-card'>"
        "<div class='t800-title'>📊 Estado de mercado</div>"
        f"<p>RSI usado: {rsi_use:.2f}</p>"
        f"<p>Dirección táctica: {tendencia}</p>"
        f"<p>Modo tormenta: {'ACTIVO' if st.session_state.estado['modo_tormenta'] else 'inactivo'}</p>"
        f"<p>Posiciones abiertas: {len(st.session_state.estado['posiciones'])}</p>"
        f"<p>Niveles en malla: {len(st.session_state.estado['ordenes_malla'])}</p>"
        "</div>",
        unsafe_allow_html=True
    )
with c_info2:
    st.markdown(
        "<div class='t800-card'>"
        "<div class='t800-title'>🎛️ Modos activos</div>"
        f"<p>Sniper: {'ON' if sniper else 'OFF'}</p>"
        f"<p>Hedging: {'ON' if hedging else 'OFF'}</p>"
        f"<p>Tormenta: {'ON' if tormenta else 'OFF'}</p>"
        f"<p>Cierre por bloque: {'ON' if cierre_bloque else 'OFF'}</p>"
        "</div>",
        unsafe_allow_html=True
    )

# ============================================================
# GUARDAR PRECIO SIEMPRE — FUERA DEL MOTOR
# ============================================================

if precio_actual:
    st.session_state.estado["precios"].append(precio_actual)
    if len(st.session_state.estado["precios"]) > 500:
        st.session_state.estado["precios"].pop(0)

#============================================================
# GRÁFICO PRECIO + RSI
# ============================================================

st.markdown("### 📈 Gráfico de Precio + RSI")

precios = st.session_state.estado["precios"]
rsi_hist = st.session_state.estado["rsi_hist"]

if len(precios) > 0 and len(rsi_hist) > 0:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        y=precios,
        mode="lines",
        name="Precio",
        line=dict(color="yellow", width=2)
    ))

    fig.add_trace(go.Scatter(
        y=rsi_hist,
        mode="lines",
        name="RSI",
        yaxis="y2",
        line=dict(color="purple", width=1, dash="dot")
    ))

    fig.update_layout(
        yaxis=dict(title="Precio", side="left"),
        yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100]),
        margin=dict(l=40, r=40, t=20, b=20),
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Esperando datos para mostrar el gráfico...")

# ============================================================
# TABLA DE MALLA
# ============================================================

if st.session_state.estado["ordenes_malla"]:
    st.markdown("### 🧱 Malla de Operación")
    df_malla = pd.DataFrame(st.session_state.estado["ordenes_malla"])
    st.dataframe(df_malla.tail(20), use_container_width=True)

# ============================================================
# HISTORIAL PNL
# ============================================================

if st.session_state.estado["historial_pnl"]:
    st.markdown("### 📜 Historial de PNL")
    df_hist = pd.DataFrame(st.session_state.estado["historial_pnl"])
    st.dataframe(df_hist.tail(30), use_container_width=True)
# ============================================================
# REFRESCO AUTOMÁTICO DEL GRÁFICO
# ============================================================

if grafico_tiempo_real:
    time.sleep(3)  # refresco cada 3 segundos
    st.experimental_rerun()
