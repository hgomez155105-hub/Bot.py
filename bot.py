import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN DE ACCESO (GOOGLE SHEETS) ---
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

# --- CONFIGURACIÓN PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

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
    """
    Tendencia simple combinando precio y RSI:
    - LONG si precio por encima de EMA y RSI < 70
    - SHORT si precio por debajo de EMA y RSI > 30
    """
    if len(precios) < 10:
        return "LONG"
    ema = np.mean(precios[-10:])
    precio = precios[-1]
    if precio >= ema and rsi <= 70:
        return "LONG"
    elif precio < ema and rsi >= 30:
        return "SHORT"
    else:
        # si está medio neutro, mantenemos la última dirección
        return st.session_state.get('direccion', 'LONG')

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
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
else:
    # --- ESTADO INICIAL ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0,
            'ganancia_total': 0.0,
            'posiciones': [],          # cada posición = un nivel ejecutado
            'precios_hist': [],
            'ordenes_malla': [],       # niveles de la grilla
            'ultimo_par': "",
            'historial_pnl': [],
            'direccion': 'LONG',
            'ultimo_precio': None
        })

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(
        f"## 👁️ H y G Inovaciones - "
        f"<span class='user-tag'>👤 {st.session_state.user_name}</span>",
        unsafe_allow_html=True
    )
    c_h2.image(LOGO_URL, width=70)

    # --- SIDEBAR ---
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Objetivo Binance:", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({
                'precios_hist': [],
                'posiciones': [],
                'ordenes_malla': [],
                'ultimo_par': par
            })
        
        st.divider()
        st.subheader("🔑 Conexión Exchange")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        
        st.divider()
        st.subheader("⚙️ Configuración de riesgo/agresividad")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Cantidad de Niveles", 1, 50, 10)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.2, format="%.3f") / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 10.0)

        tp_sensible = st.slider(
            "Profit Objetivo por Nivel (%)",
            0.01, 1.50, 0.08, format="%.2f"
        ) / 100

        st.divider()
        st.subheader("⚡ Respuesta a saltos de precio")
        salto_rapido = st.slider(
            "Salto de precio para modo rápido (%)",
            0.1, 2.0, 0.5, format="%.2f"
        ) / 100
        sleep_normal = st.slider("Delay normal (seg)", 0.3, 3.0, 0.8)
        sleep_rapido = st.slider("Delay rápido (seg)", 0.05, 0.5, 0.15)

        st.divider()
        debug_on = st.checkbox("👀 Ver debug interno por nivel")

        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.update({
                'posiciones': [],
                'ordenes_malla': []
            })
            st.rerun()

    # --- MOTOR DEL BOT ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            exchange = None
            if entorno == "🟡 MODO REAL" and api_k and api_s:
                exchange = conectar_binance(api_k, api_s)

            # Precio actual
            res = requests.get(
                f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD"
            ).json()
            precio_act = float(res['USD'])

            # Cálculo cambio de precio para definir velocidad de refresco
            precio_anterior = st.session_state.ultimo_precio
            st.session_state.ultimo_precio = precio_act

            if precio_anterior is not None and precio_anterior > 0:
                cambio_pct = abs(precio_act - precio_anterior) / precio_anterior
            else:
                cambio_pct = 0.0

            delay = sleep_rapido if cambio_pct >= salto_rapido else sleep_normal

            # Historial de precios
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 200:
                st.session_state.precios_hist.pop(0)
            
            rsi_val = calcular_rsi(st.session_state.precios_hist)
            tendencia_calc = obtener_tendencia(st.session_state.precios_hist, rsi_val)

            # Autoajuste de dirección solo cuando NO hay posiciones abiertas
            if not st.session_state.posiciones:
                st.session_state.direccion = tendencia_calc

            # Armado de malla inicial si no hay malla ni posiciones
            if not st.session_state.ordenes_malla and not st.session_state.posiciones:
                monto_nivel = inversion / niveles
                st.session_state.ordenes_malla = []
                for i in range(niveles):
                    if st.session_state.direccion == "LONG":
                        factor = 1 - (i * distancia)
                    else:
                        factor = 1 + (i * distancia)
                    st.session_state.ordenes_malla.append({
                        'id': i + 1,
                        'precio': round(precio_act * factor, 4),
                        'monto': round(monto_nivel, 2),
                        'estado': 'PENDIENTE'
                    })

            # Ejecución de órdenes de la malla (abre posición en ese nivel)
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit_long = st.session_state.direccion == "LONG" and precio_act <= o['precio']
                    hit_short = st.session_state.direccion == "SHORT" and precio_act >= o['precio']
                    if hit_long or hit_short:
                        if exchange:
                            side = 'buy' if st.session_state.direccion == "LONG" else 'sell'
                            try:
                                exchange.create_market_order(
                                    par, side, o['monto'] / precio_act
                                )
                            except Exception as ex:
                                st.warning(f"Orden real fallida: {ex}")

                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'

                        entrada_real = precio_act
                        if st.session_state.direccion == "LONG":
                            tp_price = entrada_real * (1 + tp_sensible)
                        else:
                            tp_price = entrada_real * (1 - tp_sensible)

                        st.session_state.posiciones.append({
                            'id_orden': o['id'],
                            'entrada': entrada_real,
                            'monto': o['monto'],
                            'tp_precio': tp_price
                        })

            # Gestión de cada posición por nivel (scalp individual SIEMPRE EN GANANCIA)
            nuevas_posiciones = []
            for pos in st.session_state.posiciones:
                entrada = pos['entrada']
                monto = pos['monto']
                tp_price = pos['tp_precio']

                if st.session_state.direccion == "LONG":
                    tp_hit = precio_act >= tp_price
                    retorno = (precio_act / entrada) - 1
                else:
                    tp_hit = precio_act <= tp_price
                    retorno = 1 - (precio_act / entrada)

                pnl_nivel = retorno * monto * lev

                if debug_on:
                    st.write(
                        f"Nivel {pos['id_orden']} | "
                        f"Dir: {st.session_state.direccion} | "
                        f"Entrada: {entrada:.4f} | TP: {tp_price:.4f} | "
                        f"Precio: {precio_act:.4f} | "
                        f"Retorno: {retorno*100:.4f}% | "
                        f"PnL: {pnl_nivel:.4f} | TP_hit: {tp_hit}"
                    )

                # Cierre SOLO si hay ganancia
                if tp_hit and pnl_nivel > 0:
                    if exchange:
                        side = 'sell' if st.session_state.direccion == "LONG" else 'buy'
                        try:
                            exchange.create_market_order(
                                par, side, monto / precio_act
                            )
                        except Exception as ex:
                            st.warning(f"Cierre real fallido (nivel): {ex}")

                    st.session_state.saldo_demo += (monto + pnl_nivel)
                    st.session_state.ganancia_total += pnl_nivel
                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"),
                        'Tipo': f"{st.session_state.direccion} - Nivel {pos['id_orden']}",
                        'Ganancia': round(pnl_nivel, 4)
                    })

                    # Rearmo ese nivel como PENDIENTE
                    for o in st.session_state.ordenes_malla:
                        if o['id'] == pos['id_orden']:
                            o['estado'] = 'PENDIENTE'
                            break
                else:
                    nuevas_posiciones.append(pos)

            st.session_state.posiciones = nuevas_posiciones

            # --- MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Wallet Balance", f"${st.session_state.saldo_demo:,.2f}")
            pnl_display = st.session_state.ganancia_total
            c3.metric("PNL Total", f"${pnl_display:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # --- GRÁFICO CON ENTRADAS, TP Y MALLA ---
            fig = go.Figure()

            # serie de precio
            fig.add_trace(go.Scatter(
                y=st.session_state.precios_hist,
                name="Precio",
                line=dict(color='#F0B90B', width=3)
            ))

            # puntos de entrada de posiciones abiertas
            if st.session_state.posiciones:
                x_idx = [len(st.session_state.precios_hist) - 1] * len(st.session_state.posiciones)
                fig.add_trace(go.Scatter(
                    x=x_idx,
                    y=[p['entrada'] for p in st.session_state.posiciones],
                    mode='markers',
                    name='Entradas abiertas',
                    marker=dict(color='cyan', size=10, symbol='triangle-up')
                ))
                # TPs de esas posiciones
                fig.add_trace(go.Scatter(
                    x=x_idx,
                    y=[p['tp_precio'] for p in st.session_state.posiciones],
                    mode='markers',
                    name='TP por nivel',
                    marker=dict(color='lime', size=9, symbol='x')
                ))

            # niveles de malla (pendientes y ejecutados) como líneas horizontales suaves
            if st.session_state.ordenes_malla:
                x0 = 0
                x1 = len(st.session_state.precios_hist) - 1
                for o in st.session_state.ordenes_malla:
                    color = 'gray' if o['estado'] == 'PENDIENTE' else '#F39C12'
                    fig.add_hline(
                        y=o['precio'],
                        line=dict(color=color, width=1, dash='dot'),
                        opacity=0.4,
                    )

            fig.update_layout(
                height=400,
                template="plotly_dark",
                margin=dict(l=0, r=0, b=0, t=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Malla de Operación")
            st.dataframe(st.session_state.ordenes_malla, use_container_width=True)

            st.subheader("📈 Historial de PNL por nivel")
            if st.session_state.historial_pnl:
                st.dataframe(st.session_state.historial_pnl, use_container_width=True)

            time.sleep(delay)
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(3)
            st.rerun()
