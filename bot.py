import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"
st.set_page_config(
    page_title="H y G Inovaciones",
    layout="wide",
    page_icon=LOGO_URL
)
# ============================================================
# ESTILOS VISUALES
# ============================================================
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0B0E11 !important; }}
    .user-tag {{ background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }}
    [data-testid="stMetricValue"] {{ color: #F0B90B !important; font-size: 1.8rem !important; }}
    h1, h2, h3 {{ color: white !important; }}
    </style>
    <div style='text-align: center; margin-top: -30px;'>
        <img src="{LOGO_URL}" width="120">
        <h1 style='color: white;'>H y G Inovaciones – Admin</h1>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.image(LOGO_URL, width=150)

# ============================================================
# ACCESO (GOOGLE SHEETS)
# ============================================================

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

# ============================================================
# FUNCIONES TÉCNICAS
# ============================================================

def conectar_binance(api_key, secret_key):
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
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

def obtener_tendencia(precios, rsi):
    if len(precios) < 10:
        return st.session_state.get('direccion', 'LONG')
    ema = np.mean(precios[-10:])
    precio = precios[-1]
    if precio >= ema and rsi <= 70:
        return "LONG"
    elif precio < ema and rsi >= 25:
        return "SHORT"
    else:
        return st.session_state.get('direccion', 'LONG')

# ============================================================
# SNIPER INTELIGENTE (OPTIMIZADO)
# ============================================================

def sniper_inteligente(dir_o, precio_act, precio_anterior, rsi_use, volatilidad):
    micro_pico = abs(precio_act - precio_anterior) / max(precio_anterior, 0.0001)
    sensibilidad = max(0.0005, volatilidad * 0.6)
    rsi_alto = 85
    rsi_bajo = 15

    if dir_o == "LONG":
        return rsi_use < rsi_alto and micro_pico >= sensibilidad
    else:
        return rsi_use > rsi_bajo and micro_pico >= sensibilidad

# ============================================================
# LOGIN + HEADER + BIENVENIDA (BLOQUE COMPLETO Y BLINDADO)
# ============================================================

# Inicializar variable de sesión si no existe
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Si NO está autenticado → mostrar login
if not st.session_state.get("autenticado", False):

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)

        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")

        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("Acceso denegado. Verifique su base de datos.")

# Si está autenticado → mostrar header + bienvenida
else:

    # HEADER
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(
        f"## 👁️ H y G Inovaciones - "
        f"<span class='user-tag'>👤 {st.session_state.get('user_name', 'Invitado')}</span>",
        unsafe_allow_html=True
    )
    c_h2.image(LOGO_URL, width=70)

    # MENSAJE DE BIENVENIDA PERSONALIZADO
    nombre_usuario = st.session_state.get("user_name", "Invitado")

    st.markdown(f"""
    <div style="
        background-color:#1E2329;
        padding:18px;
        border-radius:12px;
        border:1px solid #F0B90B;
        margin-top:10px;
    ">
        <h3 style="color:white; margin:0;">
            👋 Bienvenido, <span style="color:#F0B90B;">{nombre_usuario}</span>
        </h3>
        <p style="color:#CCCCCC; margin-top:6px; font-size:15px;">
            El algoritmo está listo para operar en modo táctico.  
            Activá Hedging, Sniper o Tormenta desde la barra lateral según tu estrategia.
        </p>
    </div>
    """, unsafe_allow_html=True)
# ============================================================
# ESTADO INICIAL
# ============================================================

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
        'modo_tormenta_activo': False
    })

# ============================================================
# HEADER
# ============================================================

c_h1, c_h2 = st.columns([4, 1])
c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.get('user_name, invitado')}" </span>", unsafe_allow_html=True)
c_h2.image(LOGO_URL, width=70)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.image(LOGO_URL, width=100)

    par = st.selectbox("🎯 Objetivo Binance:", obtener_top_20_binance())
    if par != st.session_state.ultimo_par:
        st.session_state.update({
            'precios_hist': [],
            'posiciones': [],
            'ordenes_malla': [],
            'rsi_hist': [],
            'ultimo_par': par
        })

    st.divider()
    st.subheader("🔑 Conexión Exchange")
    entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
    api_k = st.text_input("API Key", type="password")
    api_s = st.text_input("Secret Key", type="password")

    st.divider()
    st.subheader("⚙️ Configuración de riesgo/agresividad")
    lev = st.slider("Apalancamiento", 1, 50, 22)
    niveles = st.number_input("Cantidad de Niveles por malla", 1, 50, 7)
    distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05, format="%.3f") / 100
    inversion = st.number_input("Inversión Total por malla (USDT)", 10.0, 10000.0, 10.0)

    tp_sensible = st.slider(
        "Profit Objetivo por Nivel (%)",
        0.01, 1.50, 0.03, format="%.3f"
    ) / 100

    st.divider()
    st.subheader("🎯 RSI (auto / manual)")
    rsi_manual = st.slider("RSI Manual (0 = automático)", 0, 100, 0)

    st.divider()
    st.subheader("🧠 Modos tácticos")
    hedging_on = st.checkbox("🌀 Hedging dinámico (LONG & SHORT simultáneos)", value=True)
    sniper_on = st.checkbox("🎯 Modo Sniper (entradas en micro-picos)", value=True)
    tormenta_on = st.checkbox("🌩️ Modo Tormenta (ráfagas en alta volatilidad)", value=True)
    cierre_bloque = st.checkbox("🧱 Cierre por bloque si PnL total > 0")
    debug_on = st.checkbox("👀 Ver debug interno por nivel")

    st.divider()
    st.subheader("⚡ Respuesta a saltos de precio")
    salto_rapido = st.slider("Salto de precio para modo rápido (%)", 0.1, 2.0, 0.5, format="%.2f") / 100
    sleep_normal = st.slider("Delay normal (seg)", 0.2, 3.0, 0.7)
    sleep_rapido = st.slider("Delay rápido (seg)", 0.03, 0.5, 0.12)

    if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
        st.session_state.update({
            'posiciones': [],
            'ordenes_malla': [],
            'modo_tormenta_activo': False
        })
        st.rerun()

# ============================================================
# MOTOR DEL BOT
# ============================================================

bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")

if bot_on:
    try:
        # Conexión real si corresponde
        exchange = None
        if entorno == "🟡 MODO REAL" and api_k and api_s:
            exchange = conectar_binance(api_k, api_s)

        # Precio actual
        res = requests.get(
            f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD"
        ).json()
        precio_act = float(res['USD'])

        # Cambio de precio
        precio_anterior = st.session_state.ultimo_precio
        st.session_state.ultimo_precio = precio_act

        if precio_anterior:
            cambio_pct = abs(precio_act - precio_anterior) / precio_anterior
        else:
            cambio_pct = 0.0

        # Tormenta
        if tormenta_on and cambio_pct >= salto_rapido:
            st.session_state.modo_tormenta_activo = True
            delay = sleep_rapido
        else:
            st.session_state.modo_tormenta_activo = False
            delay = sleep_normal

        # Historial de precios
        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 300:
            st.session_state.precios_hist.pop(0)

        # RSI
        rsi_real = calcular_rsi(st.session_state.precios_hist)
        rsi_use = rsi_manual if rsi_manual != 0 else rsi_real

        st.session_state.rsi_hist.append(rsi_use)
        if len(st.session_state.rsi_hist) > 300:
            st.session_state.rsi_hist.pop(0)

        # Tendencia
        tendencia_calc = obtener_tendencia(st.session_state.precios_hist, rsi_use)
        st.session_state.direccion = tendencia_calc

        # ============================================================
        # ARMADO / ACTUALIZACIÓN DE MALLAS
        # ============================================================

        direcciones_malla = {o['dir'] for o in st.session_state.ordenes_malla}

        if hedging_on:
            # Asegurar malla en la dirección actual
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
            # Sin hedging: limpiar mallas contrarias
            st.session_state.ordenes_malla = [
                o for o in st.session_state.ordenes_malla if o['dir'] == tendencia_calc
            ]

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
    # ============================================================
        # EJECUCIÓN DE ÓRDENES DE MALLA (TU BLOQUE REEMPLAZADO)
        # ============================================================

        for o in st.session_state.ordenes_malla:
            if o['estado'] != 'PENDIENTE':
                continue

            dir_o = o['dir']
            precio_nivel = o['precio']

            # Lógica base
            if dir_o == "LONG":
                hit_basico = precio_act <= precio_nivel
            else:
                hit_basico = precio_act >= precio_nivel

            # Sniper inteligente
            if sniper_on:
                sniper_ok = sniper_inteligente(
                    dir_o,
                    precio_act,
                    precio_anterior,
                    rsi_use,
                    cambio_pct
                )
                hit = hit_basico and sniper_ok
            else:
                hit = hit_basico

            # Ejecutar orden
            if hit:
                entrada_real = precio_act
                tp_factor = tp_sensible * (0.7 if st.session_state.modo_tormenta_activo else 1.0)

                if dir_o == "LONG":
                    tp_price = entrada_real * (1 + tp_factor)
                else:
                    tp_price = entrada_real * (1 - tp_factor)

                st.session_state.posiciones.append({
                    'id_orden': o['id'],
                    'entrada': entrada_real,
                    'monto': o['monto'],
                    'tp_precio': tp_price,
                    'dir': dir_o
                })

                o['estado'] = 'EJECUTADA'

        # ============================================================
        # GESTIÓN DE POSICIONES (TP + ESCAPE + HEDGE)
        # ============================================================

        nuevas_posiciones = []
        pnl_niveles = []

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
            pnl_niveles.append((pos, pnl_nivel))

            # Escape inteligente
            tendencia_contra = (
                (dir_pos == "LONG" and tendencia_calc == "SHORT") or
                (dir_pos == "SHORT" and tendencia_calc == "LONG")
            )
            escape_ganancia = pnl_nivel > 0 and tendencia_contra

            if debug_on:
                st.write(
                    f"Nivel {pos['id_orden']} | "
                    f"Dir: {dir_pos} | Tend: {tendencia_calc} | "
                    f"Entrada: {entrada:.4f} | TP: {tp_price:.4f} | "
                    f"Precio: {precio_act:.4f} | Retorno: {retorno*100:.3f}% | "
                    f"PnL: {pnl_nivel:.4f} | TP_hit: {tp_hit} | Escape: {escape_ganancia}"
                )

            # Cierre por TP o escape
            if pnl_nivel > 0 and (tp_hit or escape_ganancia):

                # Cierre real si corresponde
                if exchange:
                    side_close = 'sell' if dir_pos == "LONG" else 'buy'
                    try:
                        exchange.create_market_order(
                            par, side_close, monto / precio_act
                        )
                    except Exception as ex:
                        st.warning(f"Cierre real fallido: {ex}")

                # Actualizar saldo demo
                st.session_state.saldo_demo += (monto + pnl_nivel)
                st.session_state.ganancia_total += pnl_nivel

                st.session_state.historial_pnl.append({
                    'Fecha': datetime.now().strftime("%H:%M:%S"),
                    'Tipo': f"{dir_pos} - Nivel {pos['id_orden']}",
                    'Ganancia': round(pnl_nivel, 4)
                })

                # Rearmar nivel
                for o in st.session_state.ordenes_malla:
                    if o['id'] == pos['id_orden'] and o['dir'] == dir_pos:
                        o['estado'] = 'PENDIENTE'
                        break

            else:
                nuevas_posiciones.append(pos)

        st.session_state.posiciones = nuevas_posiciones

        # ============================================================
        # CIERRE POR BLOQUE (OPCIONAL)
        # ============================================================

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
                            exchange.create_market_order(
                                par, side_close, monto / precio_act
                            )
                        except Exception as ex:
                            st.warning(f"Cierre real fallido (bloque): {ex}")

                    st.session_state.saldo_demo += (monto + pnl_nivel_b)
                    st.session_state.ganancia_total += pnl_nivel_b

                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"),
                        'Tipo': f"{dir_pos} - BLOQUE",
                        'Ganancia': round(pnl_nivel_b, 4)
                    })

                st.session_state.posiciones = []
                st.session_state.ordenes_malla = []

        # ============================================================
        # MÉTRICAS
        # ============================================================

        c1, c2, c3 = st.columns(3)
        c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
        c2.metric("Wallet Balance", f"${st.session_state.saldo_demo:,.2f}")
        c3.metric("PNL Total", f"${st.session_state.ganancia_total:,.2f}")

        # ============================================================
        # GRÁFICO
        # ============================================================

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            y=st.session_state.precios_hist,
            name="Precio",
            line=dict(color='#F0B90B', width=3)
        ))

        # Entradas abiertas
        if st.session_state.posiciones:
            x_idx = [len(st.session_state.precios_hist) - 1] * len(st.session_state.posiciones)

            fig.add_trace(go.Scatter(
                x=x_idx,
                y=[p['entrada'] for p in st.session_state.posiciones],
                mode='markers',
                name='Entradas',
                marker=dict(color='cyan', size=9, symbol='triangle-up')
            ))

            fig.add_trace(go.Scatter(
                x=x_idx,
                y=[p['tp_precio'] for p in st.session_state.posiciones],
                mode='markers',
                name='TP',
                marker=dict(color='lime', size=8, symbol='x')
            ))

        # Malla
        for o in st.session_state.ordenes_malla:
            fig.add_hline(
                y=o['precio'],
                line=dict(color='gray', width=1, dash='dot'),
                opacity=0.3
            )

        # RSI
        fig.add_trace(go.Scatter(
            y=st.session_state.rsi_hist,
            name="RSI",
            line=dict(color='magenta', width=2, dash='dash'),
            yaxis="y2"
        ))

        fig.update_layout(
            height=500,
            template="plotly_dark",
            margin=dict(l=0, r=0, b=0, t=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Precio"),
            yaxis2=dict(
                title="RSI",
                overlaying="y",
                side="right",
                range=[0, 100],
                showgrid=False
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        # ============================================================
        # TABLAS
        # ============================================================

        st.subheader("📋 Malla de Operación")
        st.dataframe(st.session_state.ordenes_malla, use_container_width=True)

        st.subheader("📈 Historial de PNL")
        if st.session_state.historial_pnl:
            st.dataframe(st.session_state.historial_pnl, use_container_width=True)

        time.sleep(delay)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(3)
        st.rerun()
