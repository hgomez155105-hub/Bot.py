import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

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
# CONFIGURACIÓN GENERAL
# ============================
LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

st.set_page_config(
    page_title="BOT T800 - H y G Inovaciones",
    layout="wide",
    page_icon="🤖"
)

# ============================
# TEMA MILITAR ARENA PREDADOR
# ============================
st.markdown(f"""
<style>
.stApp {{
    background-color: #F2E3C6 !important; /* Arena militar */
    color: #111111 !important;
}}
h1, h2, h3, h4, h5, h6 {{
    color: #3E4F1F !important; /* Verde oliva cazador */
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
[data-testid="stMetricDelta"] {{
    color: #8B0000 !important;
}}
.stDataFrame, .stTable {{
    background-color: #FFF !important;
    color: #111 !important;
}}
</style>
<div style='text-align: center; margin-top: -30px;'>
    <img src="{LOGO_URL}" width="120">
    <h1>BOT T800 – H y G Inovaciones</h1>
</div>
""", unsafe_allow_html=True)

st.sidebar.image(LOGO_URL, width=150)

# ============================
# FUNCIONES TÉCNICAS (PIONEX)
# ============================
def conectar_pionex(api_key, secret_key):
    try:
        exchange = ccxt.pionex({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True
        })
        return exchange
    except Exception as e:
        print("Error conectando a Pionex:", e)
        return None

def obtener_top_20_pionex():
    try:
        # Usamos Binance solo para ranking de volumen, pero operamos en Pionex
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

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
    rs = avg_gain / (avg_loss if avg_loss != 0 else 0.001)
    return 100 - (100 / (1 + rs))

def obtener_tendencia(precios, rsi):
    if len(precios) < 10:
        return st.session_state.get('direccion', 'LONG')
    ema = np.mean(precios[-10:])
    precio = precios[-1]
    if precio >= ema and rsi <= 70:
        return "LONG"
    elif precio < ema and rsi >= 30:
        return "SHORT"
    else:
        return st.session_state.get('direccion', 'LONG')

# ============================
# LOGIN
# ============================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>Acceso Táctico T800</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("Acceso denegado. Verifique su base de datos en Sheets.")
else:
    # ============================
    # ESTADO INICIAL
    # ============================
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0,
            'ganancia_total': 0.0,
            'posiciones': [],          # posiciones abiertas
            'precios_hist': [],
            'ordenes_malla': [],       # niveles de malla
            'ultimo_par': "",
            'historial_pnl': [],
            'direccion': 'LONG',
            'ultimo_precio': None,
            'rsi_hist': [],
            'modo_tormenta_activo': False,
            'eventos': []              # aperturas/cierres para el gráfico
        })

    # ============================
    # HEADER
    # ============================
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(
        f"## 🤖 BOT T800 - "
        f"<span class='user-tag'>👤 {st.session_state.user_name}</span>",
        unsafe_allow_html=True
    )
    c_h2.image(LOGO_URL, width=70)

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
        st.subheader("🔑 Conexión Exchange")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        
        st.divider()
        st.subheader("⚙️ Configuración de riesgo/agresividad")
        lev = st.slider("Apalancamiento virtual", 1, 50, 20)
        niveles = st.number_input("Cantidad de Niveles por malla", 1, 50, 7)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05, format="%.3f") / 100
        inversion = st.number_input("Inversión Total por malla (USDT)", 10.0, 10000.0, 50.0)

        tp_sensible = st.slider(
            "Profit Objetivo por Nivel (%)",
            0.01, 1.50, 0.05, format="%.3f"
        ) / 100

        st.divider()
        st.subheader("🎯 RSI (auto / manual)")
        rsi_manual = st.slider(
            "RSI Manual (0 = automático)",
            0, 100, 0
        )

        st.divider()
        st.subheader("🧠 Modos T800")
        hedging_on = st.checkbox("🌀 Hedging dinámico (LONG & SHORT)", value=True)
        sniper_on = st.checkbox("🎯 Modo Sniper (micro-picos)", value=True)
        tormenta_on = st.checkbox("🌩️ Modo Tormenta (alta volatilidad)", value=True)
        cierre_bloque = st.checkbox("🧱 Cierre por bloque si PnL total > 0")
        debug_on = st.checkbox("👀 Ver debug interno por nivel")

        st.divider()
        st.subheader("⚡ Respuesta a saltos de precio")
        salto_rapido = st.slider(
            "Salto de precio para modo rápido (%)",
            0.1, 2.0, 0.5, format="%.2f"
        ) / 100
        sleep_normal = st.slider("Delay normal (seg)", 0.2, 3.0, 0.7)
        sleep_rapido = st.slider("Delay rápido (seg)", 0.03, 0.5, 0.12)

        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.update({
                'posiciones': [],
                'ordenes_malla': [],
                'modo_tormenta_activo': False,
                'eventos': []
            })
            st.rerun()

    # ============================
    # MOTOR DEL BOT T800 (PIONEX)
    # ============================
    bot_on = st.toggle("🚀 ACTIVAR BOT T800 (PIONEX PREDADOR)")

    if bot_on:
        try:
            # --- CONEXIÓN ---
            if entorno == "🟡 MODO REAL" and api_k and api_s:
                exchange = conectar_pionex(api_k, api_s)
            else:
                exchange = None

            # --- PRECIO ACTUAL ---
            if exchange:
                ticker = exchange.fetch_ticker(par.replace("/", ""))
                precio_act = float(ticker["last"])
            else:
                base_symbol = par.split('/')[0]
                res = requests.get(
                    f"https://min-api.cryptocompare.com/data/price?fsym={base_symbol}&tsyms=USD"
                ).json()
                precio_act = float(res['USD'])

            # --- CAMBIO DE PRECIO / MODO TORMENTA ---
            precio_anterior = st.session_state.ultimo_precio
            st.session_state.ultimo_precio = precio_act

            if precio_anterior is not None and precio_anterior > 0:
                cambio_pct = abs(precio_act - precio_anterior) / precio_anterior
            else:
                cambio_pct = 0.0

            if tormenta_on and cambio_pct >= salto_rapido:
                st.session_state.modo_tormenta_activo = True
                delay = sleep_rapido
            else:
                st.session_state.modo_tormenta_activo = False
                delay = sleep_normal

            # --- HISTORIAL DE PRECIOS ---
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 300:
                st.session_state.precios_hist.pop(0)

            # --- RSI ---
            rsi_real = calcular_rsi(st.session_state.precios_hist)
            rsi_use = rsi_manual if rsi_manual != 0 else rsi_real
            st.session_state.rsi_hist.append(rsi_use)
            if len(st.session_state.rsi_hist) > 300:
                st.session_state.rsi_hist.pop(0)

            # --- TENDENCIA ---
            tendencia_calc = obtener_tendencia(st.session_state.precios_hist, rsi_use)
            st.session_state.direccion = tendencia_calc

            # ============================
            # ARMADO / ACTUALIZACIÓN DE MALLAS
            # ============================
            direcciones_malla = {o['dir'] for o in st.session_state.ordenes_malla} if st.session_state.ordenes_malla else set()

            if hedging_on:
                if st.session_state.direccion not in direcciones_malla:
                    monto_nivel = inversion / niveles
                    for i in range(niveles):
                        if st.session_state.direccion == "LONG":
                            factor = 1 - (i * distancia)
                        else:
                            factor = 1 + (i * distancia)
                        st.session_state.ordenes_malla.append({
                            'id': len(st.session_state.ordenes_malla) + 1,
                            'precio': round(precio_act * factor, 4),
                            'monto': round(monto_nivel, 2),
                            'estado': 'PENDIENTE',
                            'dir': st.session_state.direccion
                        })
            else:
                st.session_state.ordenes_malla = [
                    o for o in st.session_state.ordenes_malla if o['dir'] == st.session_state.direccion
                ]
                if st.session_state.direccion not in direcciones_malla:
                    monto_nivel = inversion / niveles
                    for i in range(niveles):
                        if st.session_state.direccion == "LONG":
                            factor = 1 - (i * distancia)
                        else:
                            factor = 1 + (i * distancia)
                        st.session_state.ordenes_malla.append({
                            'id': len(st.session_state.ordenes_malla) + 1,
                            'precio': round(precio_act * factor, 4),
                            'monto': round(monto_nivel, 2),
                            'estado': 'PENDIENTE',
                            'dir': st.session_state.direccion
                        })

            # ============================
            # EJECUCIÓN DE ÓRDENES DE MALLA
            # ============================
            nuevas_ordenes = []
            for o in st.session_state.ordenes_malla:
                if o['estado'] != 'PENDIENTE':
                    nuevas_ordenes.append(o)
                    continue

                dir_o = o['dir']
                if dir_o == "LONG":
                    hit = precio_act <= o['precio']
                else:
                    hit = precio_act >= o['precio']

                if sniper_on and st.session_state.ultimo_precio is not None:
                    micro_pico = abs(precio_act - st.session_state.ultimo_precio) / max(st.session_state.ultimo_precio, 0.0001)
                    sensibilidad = max(0.0005, cambio_pct * 0.6)
                    if dir_o == "LONG":
                        sniper_ok = (rsi_use < 80 and micro_pico >= sensibilidad)
                    else:
                        sniper_ok = (rsi_use > 20 and micro_pico >= sensibilidad)
                    hit = hit and sniper_ok

                if hit:
                    if exchange:
                        side = 'buy' if dir_o == "LONG" else 'sell'
                        try:
                            exchange.create_market_order(par, side, o['monto'] / precio_act)
                        except Exception as ex:
                            st.warning(f"Orden real fallida (nivel {o['id']}): {ex}")

                    st.session_state.saldo_demo -= o['monto']
                    o['estado'] = 'EJECUTADA'

                    tp_factor = tp_sensible * (0.7 if st.session_state.modo_tormenta_activo else 1.0)
                    if dir_o == "LONG":
                        tp_price = precio_act * (1 + tp_factor)
                    else:
                        tp_price = precio_act * (1 - tp_factor)

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
            # GESTIÓN DE POSICIONES (SCALP + ESCAPE + BLOQUE)
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

                tendencia_contra = (dir_pos == "LONG" and tendencia_calc == "SHORT") or \
                                   (dir_pos == "SHORT" and tendencia_calc == "LONG")
                escape_ganancia = pnl_nivel > 0 and tendencia_contra

                if debug_on:
                    st.write(
                        f"Nivel {pos['id_orden']} | Dir_pos: {dir_pos} | Tend_calc: {tendencia_calc} | "
                        f"Entrada: {entrada:.4f} | TP: {tp_price:.4f} | Precio: {precio_act:.4f} | "
                        f"Retorno: {retorno*100:.4f}% | PnL: {pnl_nivel:.4f} | "
                        f"TP_hit: {tp_hit} | Escape_ganancia: {escape_ganancia}"
                    )

                if pnl_nivel > 0 and (tp_hit or escape_ganancia):
                    if exchange:
                        side_close = 'sell' if dir_pos == "LONG" else 'buy'
                        try:
                            exchange.create_market_order(par, side_close, monto / precio_act)
                        except Exception as ex:
                            st.warning(f"Cierre real fallido (nivel): {ex}")

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
                    })

                    for o in st.session_state.ordenes_malla:
                        if o['id'] == pos['id_orden'] and o['dir'] == dir_pos:
                            o['estado'] = 'PENDIENTE'
                            break
                else:
                    nuevas_posiciones.append(pos)

            st.session_state.posiciones = nuevas_posiciones

            # --- CIERRE POR BLOQUE ---
            if cierre_bloque and st.session_state.posiciones:
                pnl_total_bloque = 0.0
                for pos in st.session_state.posiciones:
                    entrada = pos['entrada']
                    monto = pos['monto']
                    dir_pos = pos['dir']
                    if dir_pos == "LONG":
                        retorno_b = (precio_act / entrada) - 1
                    else:
                        retorno_b = 1 - (precio_act / entrada)
                    pnl_total_bloque += retorno_b * monto * lev

                if pnl_total_bloque > 0:
                    for pos in st.session_state.posiciones:
                        entrada = pos['entrada']
                        monto = pos['monto']
                        dir_pos = pos['dir']
                        if dir_pos == "LONG":
                            retorno_b = (precio_act / entrada) - 1
                            side_close = 'sell'
                        else:
                            retorno_b = 1 - (precio_act / entrada)
                            side_close = 'buy'
                        pnl_nivel_b = retorno_b * monto * lev

                        if exchange:
                            try:
                                exchange.create_market_order(par, side_close, monto / precio_act)
                            except Exception as ex:
                                st.warning(f"Cierre real fallido (bloque): {ex}")

                        st.session_state.saldo_demo += (monto + pnl_nivel_b)
                        st.session_state.ganancia_total += pnl_nivel_b
                        st.session_state.historial_pnl.append({
                            'Fecha': datetime.now().strftime("%H:%M:%S"),
                            'Tipo': f"{dir_pos}
