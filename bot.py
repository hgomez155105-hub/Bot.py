import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_OJO = "https://i.ibb.co/LzfNfXz/1000266017.png"

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

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_OJO, width=150)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
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
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_OJO, width=50)

    # --- SIDEBAR ---
    with st.sidebar:
        par = st.selectbox("🎯 Objetivo Binance:", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par}); st.rerun()
        
        st.divider()
        st.subheader("🔑 Conexión")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        
        st.divider()
        st.subheader("⚙️ Parámetros")
        lev = st.slider("Apalancamiento", 1, 50, 50)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.1) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
        tp_global = st.slider("Take Profit (%)", 0.01, 2.0, 0.15) / 100
        
        if st.button("🚨 BOTÓN DE PÁNICO", use_container_width=True):
            st.session_state.update({'posiciones': [], 'ordenes_malla': []})
            st.rerun()

    # --- LÓGICA DEL BOT ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

            # 1. CREAR MALLA SI NO EXISTE
            if not st.session_state.ordenes_malla:
                monto_n = inversion / 10
                for i in range(10):
                    p_nivel = precio_act * (1 - (i * distancia))
                    st.session_state.ordenes_malla.append({'id': i+1, 'precio': round(p_nivel, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'})

            # 2. EJECUTAR ÓRDENES
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE' and precio_act <= o['precio']:
                    if st.session_state.saldo_demo >= o['monto']:
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # 3. CIERRE POR PROFIT
            if st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                ganancia = (t_inv * (precio_act / p_prom - 1)) * lev

                if precio_act >= p_prom * (1 + tp_global):
                    st.session_state.historial_pnl.append({'Fecha': datetime.now().strftime("%H:%M:%S"), 'Ganancia': round(ganancia, 2)})
                    st.session_state.saldo_demo += (t_inv + ganancia)
                    st.session_state.ganancia_total += ganancia
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- VISUALIZACIÓN ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Precio", f"${precio_act:,.2f}")
            c2.metric("Saldo", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("Ganancia Total", f"${st.session_state.ganancia_total:,.2f}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3)))
            for o in st.session_state.ordenes_malla:
                fig.add_hline(y=o['precio'], line_dash="dash", line_color="green" if o['estado'] == 'EJECUTADA' else "grey")
            fig.update_layout(height=350, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a: st.subheader("📋 Malla"); st.dataframe(st.session_state.ordenes_malla, use_container_width=True)
            with col_b: st.subheader("📜 Historial"); st.dataframe(st.session_state.historial_pnl[::-1], use_container_width=True)

            time.sleep(1); st.rerun()
        except: time.sleep(1); st.rerun()
