import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt  # Librería para conectar con Binance

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="BOT T800", layout="wide", page_icon="🤖")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    h1, h2, h3 { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# --- FUNCIONES TÉCNICAS ---
def conectar_binance(api_key, secret_key):
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # Cambiar a 'spot' si no usas futuros
        })
        return exchange
    except:
        return None

def obtener_top_20_binance():
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

def obtener_tendencia(precios):
    if len(precios) < 10:
        return "LONG"
    ema = np.mean(precios[-10:])
    return "LONG" if precios[-1] >= ema else "SHORT"

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>BOT T800</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            st.session_state.autenticado = True
            st.session_state.user_name = u
            st.rerun()
else:
    # --- ESTADO INICIAL ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.saldo_demo = 1000.0
        st.session_state.ganancia_total = 0.0
        st.session_state.posiciones = []
        st.session_state.precios_hist = []
        st.session_state.ordenes_malla = []
        st.session_state.ultimo_par = ""
        st.session_state.historial_pnl = []
        st.session_state.direccion = 'LONG'
        st.session_state.max_pnl_alcanzado = 0.0

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(
        f"## 🤖 BOT T800 - <span class='user-tag'>👤 {st.session_state.user_name}</span>",
        unsafe_allow_html=True
    )
    c_h2.image(LOGO_URL, width=70)

    # --- SIDEBAR ---
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Objetivo Binance:", obtener_top_20_binance())

        # RESET TÁCTICO AL CAMBIAR DE PAR
        if par != st.session_state.ultimo_par:
            st.session_state.ultimo_par = par
            st.session_state.precios_hist = []
            st.session_state.posiciones = []
            st.session_state.ordenes_malla = []
            st.session_state.max_pnl_alcanzado = 0.0

        st.divider()
        st.subheader("🔑 Conexión Exchange")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")

        st.divider()
        st.subheader("⚙️ Configuración base")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Cantidad de Niveles", 1, 50, 10)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.2) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        tp_sensible = st.slider("Profit Objetivo base (%)", 0.005, 1.0, 0.1, format="%.3f") / 100

        st.subheader("🧠 Modos tácticos T800")
        sniper = st.checkbox("🎯 Modo Sniper (scalp agresivo)", True)
        hedging = st.checkbox("🌀 Hedging dinámico", True)
        tormenta = st.checkbox("🌩️ Modo Tormenta (alta volatilidad)", True)
        cierre_bloque = st.checkbox("🧱 Cierre por bloque si PnL total > 0", False)

        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.posiciones = []
            st.session_state.ordenes_malla = []
            st.session_state.max_pnl_alcanzado = 0.0
            st.rerun()

    # --- AJUSTES SEGÚN MODOS ---
    tp_objetivo = tp_sensible
    distancia_malla = distancia
    sleep_time = 1.0

    if sniper:
        tp_objetivo = tp_sensible * 0.5  # toma ganancias más chicas, más seguido
    if tormenta:
        distancia_malla = distancia * 0.7  # malla más apretada
        sleep_time = 0.7  # responde más rápido

    # --- MOTOR T800 ---
    bot_on = st.toggle("🚀 ACTIVAR BOT T800")

    if bot_on:
        try:
            # Conexión Real si aplica
            exchange = None
            if entorno == "🟡 MODO REAL" and api_k and api_s:
                exchange = conectar_binance(api_k, api_s)

            # PRECIO ACTUAL
            base_symbol = par.split('/')[0]
            res = requests.get(
                f"https://min-api.cryptocompare.com/data/price?fsym={base_symbol}&tsyms=USD"
            ).json()
            precio_act = float(res['USD'])

            # HISTORIAL DE PRECIOS (GRÁFICO + RSI)
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 200:
                st.session_state.precios_hist.pop(0)

            # RSI + TENDENCIA (AUTO-DIRECCIÓN)
            rsi_val = calcular_rsi(st.session_state.precios_hist)
            tendencia = obtener_tendencia(st.session_state.precios_hist)
            st.session_state.direccion = tendencia  # siempre se auto-orienta LONG/SHORT

            # 1. ENTRADA EN MALLA (T800 AGRESIVO)
            if not st.session_state.ordenes_malla and not st.session_state.posiciones:
                if (tendencia == "LONG" and rsi_val <= 55) or (tendencia == "SHORT" and rsi_val >= 45):
                    monto_nivel = inversion / niveles
                    for i in range(niveles):
                        factor = (1 - (i * distancia_malla)) if st.session_state.direccion == "LONG" else (1 + (i * distancia_malla))
                        st.session_state.ordenes_malla.append({
                            'id': i + 1,
                            'precio': round(precio_act * factor, 4),
                            'monto': round(monto_nivel, 2),
                            'estado': 'PENDIENTE'
                        })

            # 2. EJECUCIÓN (REAL O DEMO)
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit = (st.session_state.direccion == "LONG" and precio_act <= o['precio']) or \
                          (st.session_state.direccion == "SHORT" and precio_act >= o['precio'])
                    if hit:
                        if exchange:  # Si es REAL
                            side = 'buy' if st.session_state.direccion == "LONG" else 'sell'
                            exchange.create_market_order(par, side, o['monto'] / precio_act)

                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # 3. CIERRE CON TRAILING PROFIT (SIEMPRE EN GANANCIA)
            pnl_actual = 0
            if st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                if st.session_state.direccion == "LONG":
                    pnl_actual = (precio_act / p_prom - 1) * t_inv * lev
                else:
                    pnl_actual = (1 - precio_act / p_prom) * t_inv * lev

                # Objetivo agresivo
                if pnl_actual >= (t_inv * tp_objetivo * lev):
                    if pnl_actual > st.session_state.max_pnl_alcanzado:
                        st.session_state.max_pnl_alcanzado = pnl_actual

                    # Trailing: si retrocede 2% desde el máximo, cierra
                    if pnl_actual < (st.session_state.max_pnl_alcanzado * 0.98):
                        if exchange:  # Cierre en REAL
                            side = 'sell' if st.session_state.direccion == "LONG" else 'buy'
                            exchange.create_market_order(par, side, t_inv / precio_act)

                        st.session_state.historial_pnl.append({
                            'Fecha': datetime.now().strftime("%H:%M:%S"),
                            'Tipo': st.session_state.direccion,
                            'Ganancia': round(pnl_actual, 4)
                        })
                        st.session_state.saldo_demo += (t_inv + pnl_actual)
                        st.session_state.ganancia_total += pnl_actual
                        st.session_state.posiciones = []
                        st.session_state.ordenes_malla = []
                        st.session_state.max_pnl_alcanzado = 0.0
                        st.rerun()

            # 4. HEDGING DINÁMICO (CAMBIO DE DIRECCIÓN EN PERDIDA CONTROLADA)
            if hedging and st.session_state.posiciones and pnl_actual < 0:
                # Si RSI se da vuelta fuerte contra la posición, resetea y cambia de lado
                if (st.session_state.direccion == "LONG" and rsi_val < 40) or \
                   (st.session_state.direccion == "SHORT" and rsi_val > 60):
                    st.session_state.posiciones = []
                    st.session_state.ordenes_malla = []
                    st.session_state.max_pnl_alcanzado = 0.0
                    st.session_state.direccion = "SHORT" if st.session_state.direccion == "LONG" else "LONG"

            # 5. CIERRE POR BLOQUE (GANANCIA TOTAL POSITIVA)
            if cierre_bloque and st.session_state.ganancia_total > 0 and st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                if st.session_state.direccion == "LONG":
                    pnl_actual = (precio_act / p_prom - 1) * t_inv * lev
                else:
                    pnl_actual = (1 - precio_act / p_prom) * t_inv * lev

                if pnl_actual > 0:
                    if exchange:
                        side = 'sell' if st.session_state.direccion == "LONG" else 'buy'
                        exchange.create_market_order(par, side, t_inv / precio_act)

                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"),
                        'Tipo': st.session_state.direccion,
                        'Ganancia': round(pnl_actual, 4)
                    })
                    st.session_state.saldo_demo += (t_inv + pnl_actual)
                    st.session_state.ganancia_total += pnl_actual
                    st.session_state.posiciones = []
                    st.session_state.ordenes_malla = []
                    st.session_state.max_pnl_alcanzado = 0.0
                    st.rerun()

            # --- UI MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Wallet DEMO", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("PNL Total", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # --- GRÁFICO VIVO PRECIO + RSI ---
            st.markdown("### 📈 Gráfico de Precio + RSI")

            precios = st.session_state.precios_hist
            if len(precios) > 1:
                fig = go.Figure()
                # Precio
                fig.add_trace(go.Scatter(
                    y=precios,
                    name="Precio",
                    mode="lines",
                    line=dict(color="#F0B90B", width=3)
                ))
                # RSI (recalculado incremental)
                rsi_series = [calcular_rsi(precios[:i]) for i in range(2, len(precios) + 1)]
                fig.add_trace(go.Scatter(
                    y=rsi_series,
                    name="RSI",
                    mode="lines",
                    yaxis="y2",
                    line=dict(color="purple", width=1, dash="dot")
                ))

                fig.update_layout(
                    height=400,
                    template="plotly_dark",
                    margin=dict(l=0, r=0, b=0, t=0),
                    showlegend=True,
                    yaxis=dict(title="Precio", side="left"),
                    yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100])
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Esperando datos de precio para dibujar el gráfico...")

            # --- MALLA ---
            st.subheader("📋 Malla de Operación")
            if st.session_state.ordenes_malla:
                st.dataframe(pd.DataFrame(st.session_state.ordenes_malla), use_container_width=True)
            else:
                st.write("Sin órdenes en malla por el momento.")

            # --- HISTORIAL PNL ---
            st.subheader("📜 Historial de PnL")
            if st.session_state.historial_pnl:
                df_hist = pd.DataFrame(st.session_state.historial_pnl)
                st.dataframe(df_hist.tail(30), use_container_width=True)
            else:
                st.write("Sin operaciones cerradas aún.")

            # LOOP REAL-TIME
            time.sleep(sleep_time)
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(5)
            st.rerun()
    else:
        st.info("Bot T800 apagado. Activá el algoritmo para iniciar el escaneo táctico.")
