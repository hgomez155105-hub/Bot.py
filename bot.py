import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="☀️")

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

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    </style>
    """, unsafe_allow_html=True)

LOGO_SOL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Sol_de_Mayo-Bandera_de_Argentina.svg/1200px-Sol_de_Mayo-Bandera_de_Argentina.svg.png"

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_SOL, width=120)
        st.title("H y G Inovaciones")
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA"):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
            'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
            'historial_pnl': [], 'direccion': 'LONG'
        })

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## ☀️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_SOL, width=50)

    # --- SIDEBAR ---
    with st.sidebar:
        par = st.selectbox("🎯 Objetivo (Top 20 Binance):", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par}); st.rerun()
        
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 30, 10)
        distancia = st.slider("Distancia entre niveles (%)", 0.01, 2.0, 0.1) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        
        st.subheader("🛠️ Parámetros de Caza")
        rsi_compra = st.slider("RSI Entrada", 10, 70, 45)
        tp_global = st.slider("Take Profit (%)", 0.01, 5.0, 0.2) / 100

    # --- LÓGICA DE DETECCIÓN DE TENDENCIA ---
    def obtener_tendencia(precios):
        if len(precios) < 10: return "LONG"
        ema = sum(precios[-10:]) / 10
        return "LONG" if precios[-1] >= ema else "SHORT"

    # --- BOT EN ACCIÓN ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            rsi_val = calcular_rsi(st.session_state.precios_hist)
            tendencia_actual = obtener_tendencia(st.session_state.precios_hist)

            # 1. DISPARAR MALLA SEGÚN TENDENCIA (SOLUCIONA EL ATRAPO)
            if not st.session_state.ordenes_malla:
                if (tendencia_actual == "LONG" and rsi_val <= rsi_compra) or (tendencia_actual == "SHORT" and rsi_val >= (100 - rsi_compra)):
                    st.session_state.direccion = tendencia_actual
                    monto_n = inversion / niveles
                    for i in range(niveles):
                        # Si es LONG, compra abajo. Si es SHORT, vende arriba.
                        factor = (1 - (i * distancia)) if st.session_state.direccion == "LONG" else (1 + (i * distancia))
                        p_nivel = precio_act * factor
                        st.session_state.ordenes_malla.append({'id': i+1, 'precio': round(p_nivel, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'})
                    st.toast(f"🎯 Modo {st.session_state.direccion} Activado")

            # 2. EJECUCIÓN DE ÓRDENES
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit = (st.session_state.direccion == "LONG" and precio_act <= o['precio']) or \
                          (st.session_state.direccion == "SHORT" and precio_act >= o['precio'])
                    if hit:
                        if st.session_state.saldo_demo >= o['monto']:
                            st.session_state.saldo_demo -= o['monto']
                            o['estado'] = 'EJECUTADA'
                            st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # 3. CIERRE POR PROFIT (PICOTEO AGRESIVO)
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                
                if st.session_state.direccion == "LONG":
                    ganancia_actual = (sum(p['monto'] for p in st.session_state.posiciones) * (precio_act / p_prom - 1)) * lev
                    condicion_cierre = precio_act >= p_prom * (1 + tp_global)
                else:
                    ganancia_actual = (sum(p['monto'] for p in st.session_state.posiciones) * (1 - precio_act / p_prom)) * lev
                    condicion_cierre = precio_act <= p_prom * (1 - tp_global)

                if condicion_cierre and ganancia_actual > 0:
                    total_monto = sum(p['monto'] for p in st.session_state.posiciones)
                    st.session_state.historial_pnl.append({'Fecha': datetime.now().strftime("%H:%M:%S"), 'Par': par, 'Tipo': st.session_state.direccion, 'Ganancia': round(ganancia_actual, 2)})
                    st.session_state.saldo_demo += (total_monto + ganancia_actual)
                    st.session_state.ganancia_total += ganancia_actual
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- PANEL VISUAL ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Saldo Disponible", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("Cosecha Total", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3)))
            for o in st.session_state.ordenes_malla:
                fig.add_hline(y=o['precio'], line_dash="dash", line_color="green" if o['estado'] == 'EJECUTADA' else "grey")
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a: st.subheader("📋 Malla"); st.table(st.session_state.ordenes_malla)
            with col_b: st.subheader("📜 Historial"); st.table(st.session_state.historial_pnl[::-1])

            time.sleep(1); st.rerun()
        except: time.sleep(1); st.rerun()
    
