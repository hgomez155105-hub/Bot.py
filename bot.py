import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- ESTILO VISUAL (LOGO DEL OJO SIEMPRE PRESENTE) ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    h1, h2, h3 { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# URL del Logo del Ojo que me pasaste
LOGO_URL = "https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png"

# --- FUNCIONES TÉCNICAS (SE MANTIENE TODO) ---
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

# --- LOGIN CON LOGO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_URL, width=200) # Logo en el Login
        st.markdown("<h2 style='text-align: center;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    # --- INICIALIZACIÓN DE VARIABLES ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
                                 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
                                 'historial_pnl': [], 'direccion': 'LONG'})

    # --- HEADER CON LOGO ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_URL, width=70) # Logo en la Interfaz

    # --- SIDEBAR (CON TODOS LOS CONTROLES) ---
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
        st.subheader("⚙️ Configuración de Malla")
        lev = st.slider("Apalancamiento", 1, 50, 50)
        niveles = st.number_input("Cantidad de Niveles", 1, 50, 10) # Hasta 50 niveles
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05) / 100 # Default más pegado
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        
        st.subheader("🛠️ Caza Agresiva")
        rsi_limite = st.slider("RSI Entrada", 10, 90, 50)
        tp_global = st.slider("Take Profit (%)", 0.01, 2.0, 0.05) / 100 # Default super agresivo (0.05%)
        
        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.update({'posiciones': [], 'ordenes_malla': []}); st.rerun()

    # --- ALGORITMO PREDADOR AGRESIVO ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            # Obtención de precio rápida
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            
            rsi_val = calcular_rsi(st.session_state.precios_hist)
            tendencia = obtener_tendencia(st.session_state.precios_hist)

            # 1. ANÁLISIS Y ENTRADA (SE MANTIENE LÓGICA DE DIRECCIÓN)
            if not st.session_state.ordenes_malla:
                if (tendencia == "LONG" and rsi_val <= rsi_limite) or (tendencia == "SHORT" and rsi_val >= (100 - rsi_limite)):
                    st.session_state.direccion = tendencia
                    monto_nivel = inversion / niveles
                    for i in range(niveles):
                        factor = (1 - (i * distancia)) if st.session_state.direccion == "LONG" else (1 + (i * distancia))
                        st.session_state.ordenes_malla.append({
                            'id': i+1, 'precio': round(precio_act * factor, 4), 
                            'monto': round(monto_nivel, 2), 'estado': 'PENDIENTE'
                        })
                    st.toast(f"🎯 Malla {st.session_state.direccion} desplegada")

            # 2. EJECUCIÓN INSTANTÁNEA
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit = (st.session_state.direccion == "LONG" and precio_act <= o['precio']) or \
                          (st.session_state.direccion == "SHORT" and precio_act >= o['precio'])
                    if hit and st.session_state.saldo_demo >= o['monto']:
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # 3. CIERRE AGRESIVO (PICOTEO EN POSITIVO SIEMPRE)
            if st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                
                if st.session_state.direccion == "LONG":
                    pnl = (t_inv * (precio_act / p_prom - 1)) * lev
                    condicion_cierre = precio_act >= p_prom * (1 + tp_global)
                else:
                    pnl = (t_inv * (1 - precio_act / p_prom)) * lev
                    condicion_cierre = precio_act <= p_prom * (1 - tp_global)

                # Si toca el TP o hay ganancia mínima y el mercado se gira, CERRAMOS
                if condicion_cierre and pnl > 0:
                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"), 
                        'Tipo': st.session_state.direccion, 
                        'Ganancia': round(pnl, 2)
                    })
                    st.session_state.saldo_demo += (t_inv + pnl)
                    st.session_state.ganancia_total += pnl
                    # REINICIO INMEDIATO PARA VOLVER A ENTRAR
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- PANEL VISUAL (MANTENIDO) ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Wallet", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("Cosecha Total", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # Gráfico con malla
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3)))
            for o in st.session_state.ordenes_malla:
                color_n = "green" if o['estado'] == 'EJECUTADA' else "grey"
                fig.add_hline(y=o['precio'], line_dash="dash", line_color=color_n)
            fig.update_layout(height=350, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a: st.subheader("📋 Malla Activa"); st.dataframe(st.session_state.ordenes_malla, use_container_width=True)
            with col_b: st.subheader("📜 Historial PNL"); st.dataframe(st.session_state.historial_pnl[::-1], use_container_width=True)

            time.sleep(1); st.rerun()
        except: time.sleep(1); st.rerun()
        
