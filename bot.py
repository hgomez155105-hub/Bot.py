import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN DE BASE DE DATOS (GOOGLE SHEETS) ---
# URL de tu CSV de Google Sheets para validar usuarios
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        # Leemos la base de datos de Google
        df = pd.read_csv(SHEET_URL)
        # Limpiamos nombres de columnas por si tienen espacios
        df.columns = df.columns.str.strip().str.lower()
        # Buscamos coincidencia de usuario y clave
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")
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

# --- FUNCIONES TÉCNICAS (TUYAS, SIN TOCAR) ---
def conectar_binance(api_key, secret_key):
    try:
        exchange = ccxt.binance({
            'apiKey': api_key, 'secret': secret_key,
            'enableRateLimit': True, 'options': {'defaultType': 'future'}
        })
        return exchange
    except: return None

def obtener_top_20_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except: return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios); ganancias = deltas.clip(min=0); perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:]); avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / (avg_loss if avg_loss != 0 else 0.001))))

def obtener_tendencia(precios):
    if len(precios) < 10: return "LONG"
    ema = np.mean(precios[-10:])
    return "LONG" if precios[-1] >= ema else "SHORT"

# --- LOGIN REPARADO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_URL, width=200)
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_input, p_input):
                st.session_state.autenticado = True
                st.session_state.user_name = u_input
                st.rerun()
            else:
                st.error("Credenciales inválidas. Acceso denegado.")
else:
    # --- TODO TU MOTOR ORIGINAL DESDE AQUÍ ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
                                 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
                                 'historial_pnl': [], 'direccion': 'LONG', 'max_pnl_alcanzado': 0.0})

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_URL, width=70)

    # --- SIDEBAR ---
    with st.sidebar:
        st.image(LOGO_URL, width=100)
        par = st.selectbox("🎯 Objetivo Binance:", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
        
        st.divider()
        st.subheader("🔑 Conexión Exchange")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        
        st.divider()
        st.subheader("⚙️ Configuración")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Cantidad de Niveles", 1, 50, 10)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.2) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        tp_sensible = st.slider("Profit Objetivo (%)", 0.005, 1.0, 0.1, format="%.3f") / 100
        
        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.update({'posiciones': [], 'ordenes_malla': [], 'max_pnl_alcanzado': 0.0}); st.rerun()

    # --- LÓGICA DE EJECUCIÓN (TU MOTOR) ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            exchange = None
            if entorno == "🟡 MODO REAL" and api_k and api_s:
                exchange = conectar_binance(api_k, api_s)

            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            
            rsi_val = calcular_rsi(st.session_state.precios_hist)
            tendencia = obtener_tendencia(st.session_state.precios_hist)

            if not st.session_state.ordenes_malla and not st.session_state.posiciones:
                if (tendencia == "LONG" and rsi_val <= 50) or (tendencia == "SHORT" and rsi_val >= 50):
                    st.session_state.direccion = tendencia
                    monto_nivel = inversion / niveles
                    for i in range(niveles):
                        factor = (1 - (i * distancia)) if st.session_state.direccion == "LONG" else (1 + (i * distancia))
                        st.session_state.ordenes_malla.append({
                            'id': i+1, 'precio': round(precio_act * factor, 4), 
                            'monto': round(monto_nivel, 2), 'estado': 'PENDIENTE'
                        })

            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit = (st.session_state.direccion == "LONG" and precio_act <= o['precio']) or \
                          (st.session_state.direccion == "SHORT" and precio_act >= o['precio'])
                    if hit:
                        if exchange:
                            side = 'buy' if st.session_state.direccion == "LONG" else 'sell'
                            exchange.create_market_order(par, side, o['monto'] / precio_act)
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            if st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                pnl_actual = ((precio_act / p_prom - 1) if st.session_state.direccion == "LONG" else (1 - precio_act / p_prom)) * t_inv * lev

                if pnl_actual >= (t_inv * tp_sensible * lev):
                    if pnl_actual > st.session_state.max_pnl_alcanzado:
                        st.session_state.max_pnl_alcanzado = pnl_actual
                    
                    if pnl_actual < (st.session_state.max_pnl_alcanzado * 0.98):
                        if exchange:
                            side = 'sell' if st.session_state.direccion == "LONG" else 'buy'
                            exchange.create_market_order(par, side, t_inv / precio_act)
                        st.session_state.historial_pnl.append({'Fecha': datetime.now().strftime("%H:%M:%S"), 'Tipo': st.session_state.direccion, 'Ganancia': round(pnl_actual, 4)})
                        st.session_state.saldo_demo += (t_inv + pnl_actual)
                        st.session_state.ganancia_total += pnl_actual
                        st.session_state.update({'posiciones': [], 'ordenes_malla': [], 'max_pnl_alcanzado': 0.0})
                        st.rerun()

            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Wallet Balance", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("PNL Total", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3)))
            fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Malla de Operación")
            st.dataframe(st.session_state.ordenes_malla, use_container_width=True)

            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(5); st.rerun()
