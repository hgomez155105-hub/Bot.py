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
    Tendencia agresiva combinando EMA corta + RSI:
    - LONG si precio por encima de EMA y RSI < 75
    - SHORT si precio por debajo de EMA y RSI > 25
    - Si está neutro, mantiene dirección actual
    """
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
            'posiciones': [],          # cada posición = un nivel ejecutado (LONG o SHORT)
            'precios_hist': [],
            'ordenes_malla': [],       # niveles de la grilla (LONG o SHORT)
            'ultimo_par': "",
            'historial_pnl': [],
            'direccion': 'LONG',       # dirección preferida para nuevas órdenes
            'ultimo_precio': None,
            'rsi_hist': [],
            'modo_tormenta_activo': False
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
        rsi_manual = st.slider(
            "RSI Manual (0 = automático)",
            0, 100, 0
        )

        st.divider()
        st.subheader("🧠 Modos tácticos")
        hedging_on = st.checkbox("🌀 Hedging dinámico (LONG & SHORT simultáneos)", value=True)
        sniper_on = st.checkbox("🎯 Modo Sniper (entradas en micro-picos)", value=True)
        tormenta_on = st.checkbox("🌩️ Modo Tormenta (ráfagas en alta volatilidad)", value=True)
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
                'modo_tormenta_activo': False
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

            # Cálculo cambio de precio para definir velocidad de refresco (y detectar tormenta)
            precio_anterior = st.session_state.ultimo_precio
            st.session_state.ultimo_precio = precio_act

            if precio_anterior is not None and precio_anterior > 0:
                cambio_pct = abs(precio_act - precio_anterior) / precio_anterior
            else:
                cambio_pct = 0.0

            # Modo tormenta: si hay salto fuerte, activamos ráfaga
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
            
            # RSI real y usado
            rsi_real = calcular_rsi(st.session_state.precios_hist)
            rsi_use = rsi_manual if rsi_manual != 0 else rsi_real

            st.session_state.rsi_hist.append(rsi_use)
            if len(st.session_state.rsi_hist) > 300:
                st.session_state.rsi_hist.pop(0)

            # Tendencia calculada
            tendencia_calc = obtener_tendencia(st.session_state.precios_hist, rsi_use)
            st.session_state.direccion = tendencia_calc

            # --- ARMADO / ACTUALIZACIÓN DE MALLAS ---
            # Cada malla lleva su propia dir (LONG / SHORT)
            direcciones_malla = {o['dir'] for o in st.session_state.ordenes_malla} if st.session_state.ordenes_malla else set()

            # En hedging dinámico: permitimos tener malla LONG y malla SHORT simultáneas
            # Si hedging desactivado: solo armamos malla de la dirección actual.
            if hedging_on:
                # Asegurar que exista malla en la tendencia actual
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
                # Sin hedging: limpiamos mallas de dirección contraria cuando gire tendencia
                st.session_state.ordenes_malla = [o for o in st.session_state.ordenes_malla if o['dir'] == st.session_state.direccion]
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

            # --- EJECUCIÓN DE ÓRDENES DE MALLA (MODO SNIPER + NORMAL) ---
            for o in st.session_state.ordenes_malla:
                if o['estado'] != 'PENDIENTE':
                    continue

                dir_o = o['dir']
                if dir_o == "LONG":
                    distancia_precio = (o['precio'] - precio_act) / o['precio']
                    hit_basico = precio_act <= o['precio']
                else:
                    distancia_precio = (precio_act - o['precio']) / o['precio']
                    hit_basico = precio_act >= o['precio']

                hit = hit_basico

                # Modo sniper: en lugar de solo tocar el precio de la malla,
                # exigimos micro-pico: cambio fuerte reciente + RSI en zona.
                def sniper_inteligente(dir_o, precio_act, precio_anterior, rsi_use, volatilidad):
    # Micro-pico dinámico
    micro_pico = abs(precio_act - precio_anterior) / precio_anterior

    # Sensibilidad adaptativa
    sensibilidad = max(0.001, volatilidad * 0.7)

    # Zonas RSI más flexibles
    rsi_alto = 80
    rsi_bajo = 20

    if dir_o == "LONG":
        # LONG: queremos entrar en caídas rápidas pero no en sobrecompra extrema
        if rsi_use < rsi_alto and micro_pico >= sensibilidad:
            return True
        else:
            return False

    else:  # SHORT
        # SHORT: queremos entrar en subas rápidas pero no en sobreventa extrema
        if rsi_use > rsi_bajo and micro_pico >= sensibilidad:
            return True
        else:
            return False
            if sniper_on:
    sniper_ok = sniper_inteligente(dir_o, precio_act, precio_anterior, rsi_use, cambio_pct)
    hit = hit_basico and sniper_ok
else:
    hit = hit_basico
                    # En modo tormenta, acortamos aún más el TP
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

            # --- GESTIÓN DE POSICIONES (SCALP + ESCAPE + HEDGE) ---
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

                # Escape inteligente: si hay ganancia y la tendencia va en contra de esta posición,
                # cerramos aunque no haya tocado TP exacto.
                tendencia_contra = (dir_pos == "LONG" and tendencia_calc == "SHORT") or \
                                   (dir_pos == "SHORT" and tendencia_calc == "LONG")
                escape_ganancia = pnl_nivel > 0 and tendencia_contra

                if debug_on:
                    st.write(
                        f"Nivel {pos['id_orden']} | "
                        f"Dir_pos: {dir_pos} | Tend_calc: {tendencia_calc} | "
                        f"Entrada: {entrada:.4f} | TP: {tp_price:.4f} | "
                        f"Precio: {precio_act:.4f} | "
                        f"Retorno: {retorno*100:.4f}% | "
                        f"PnL: {pnl_nivel:.4f} | TP_hit: {tp_hit} | "
                        f"Escape_ganancia: {escape_ganancia} | "
                        f"RSI_real: {rsi_real:.1f} | RSI_usado: {rsi_use:.1f} | "
                        f"Tormenta: {st.session_state.modo_tormenta_activo}"
                    )

                # Cierra SOLO si hay GANANCIA (TP alcanzado o escape por tendencia contraria)
                if pnl_nivel > 0 and (tp_hit or escape_ganancia):
                    if exchange:
                        side_close = 'sell' if dir_pos == "LONG" else 'buy'
                        try:
                            exchange.create_market_order(
                                par, side_close, monto / precio_act
                            )
                        except Exception as ex:
                            st.warning(f"Cierre real fallido (nivel): {ex}")

                    st.session_state.saldo_demo += (monto + pnl_nivel)
                    st.session_state.ganancia_total += pnl_nivel
                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"),
                        'Tipo': f"{dir_pos} - Nivel {pos['id_orden']}",
                        'Ganancia': round(pnl_nivel, 4)
                    })

                    # Rearmar el mismo nivel como PENDIENTE
                    for o in st.session_state.ordenes_malla:
                        if o['id'] == pos['id_orden'] and o['dir'] == dir_pos:
                            o['estado'] = 'PENDIENTE'
                            break
                else:
                    nuevas_posiciones.append(pos)

            st.session_state.posiciones = nuevas_posiciones

            # --- CIERRE POR BLOQUE (opcional) ---
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

            # --- MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Wallet Balance", f"${st.session_state.saldo_demo:,.2f}")
            pnl_display = st.session_state.ganancia_total
            c3.metric("PNL Total", f"${pnl_display:,.2f}", delta=f"RSI uso: {rsi_use:.1f}")

            # --- GRÁFICO CON ENTRADAS, TP, MALLA Y RSI ---
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                y=st.session_state.precios_hist,
                name="Precio",
                line=dict(color='#F0B90B', width=3)
            ))

            if st.session_state.posiciones:
                x_idx = [len(st.session_state.precios_hist) - 1] * len(st.session_state.posiciones)
                
                entrada_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                tp_prom = sum(p['tp_precio'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)

                fig.add_hline(
                    y=entrada_prom,
                    line=dict(color='cyan', width=2),
                    annotation_text="Nivel entrada",
                    annotation_position="top left"
                )

                fig.add_hline(
                    y=tp_prom,
                    line=dict(color='lime', width=2, dash='dot'),
                    annotation_text="Objetivo TP",
                    annotation_position="bottom left"
                )

                fig.add_trace(go.Scatter(
                    x=x_idx,
                    y=[p['entrada'] for p in st.session_state.posiciones],
                    mode='markers',
                    name='Entradas abiertas',
                    marker=dict(color='cyan', size=9, symbol='triangle-up')
                ))
                fig.add_trace(go.Scatter(
                    x=x_idx,
                    y=[p['tp_precio'] for p in st.session_state.posiciones],
                    mode='markers',
                    name='TP por nivel',
                    marker=dict(color='lime', size=8, symbol='x')
                ))

            if st.session_state.ordenes_malla:
                for o in st.session_state.ordenes_malla:
                    color = 'gray' if o['estado'] == 'PENDIENTE' else '#F39C12'
                    fig.add_hline(
                        y=o['precio'],
                        line=dict(color=color, width=1, dash='dot'),
                        opacity=0.3,
                    )

            if st.session_state.rsi_hist:
                fig.add_trace(go.Scatter(
                    y=st.session_state.rsi_hist,
                    name="RSI (uso)",
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

            st.subheader("📋 Malla de Operación")
            st.dataframe(st.session_state.ordenes_malla, use_container_width=True)

            st.subheader("📈 Historial de PNL por nivel / bloque")
            if st.session_state.historial_pnl:
                st.dataframe(st.session_state.historial_pnl, use_container_width=True)

            time.sleep(delay)
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(3)
            st.rerun()
