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

# --- ESTILOS ---
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
        if st.button("INGRESAR"):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 'historial_pnl': []})

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## ☀️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_SOL, width=50)

    # --- SIDEBAR ---
    with st.sidebar:
        par = st.selectbox("Monedas en Tendencia:", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par}); st.rerun()
        
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        st.text_input("API Key", type="password"); st.text_input("Secret Key", type="password")
        
        st.subheader("⚙️ Configuración")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Órdenes de Malla", 1, 20, 5)
        distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0.5) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        
        st.subheader("🛡️ RSI & Profit")
        rsi_compra = st.slider("RSI Entrada (Compra)", 10, 50, 30)
        rsi_venta = st.slider("RSI Salida (Venta)", 50, 90, 70)
        tp_global = st.slider("Take Profit (%)", 0.1, 10.0, 0.5) / 100

    # --- EJECUCIÓN DEL BOT ---
    bot_on = st.toggle("EJECUTAR ALGORITMO")
    if bot_on:
        try:
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)
            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # 1. Crear Malla (Solo si RSI es bajo)
            if not st.session_state.ordenes_malla and rsi_val <= rsi_compra:
                monto_n = inversion / niveles
                for i in range(niveles):
                    p_nivel = precio_act * (1 - (i * distancia))
                    st.session_state.ordenes_malla.append({'id': i+1, 'precio': round(p_nivel, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'})

            # 2. Ejecutar Compras y Descontar Saldo
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE' and precio_act <= o['precio']:
                    if st.session_state.saldo_demo >= o['monto']:
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})
                        st.toast(f"Comprado nivel {o['id']} de {par}")

            # 3. Lógica de Venta con SEGURO ANTI-PÉRDIDA
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                p_tp = p_prom * (1 + tp_global)
                
                # Calculamos ganancia actual incluyendo apalancamiento
                total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                ganancia_actual = (total_inv * (precio_act / p_prom - 1)) * lev

                # CONDICIÓN BLINDADA: 
                # Cierra si toca el Profit O si el RSI es alto PERO la ganancia es positiva
                if precio_act >= p_tp or (rsi_val >= rsi_venta and ganancia_actual > 0):
                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"), 
                        'Par': par, 
                        'Ganancia': round(ganancia_actual, 2)
                    })
                    st.session_state.saldo_demo += (total_inv + ganancia_actual)
                    st.session_state.ganancia_total += ganancia_actual
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- VISUALIZACIÓN ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio", f"${precio_act:,.4f}")
            c2.metric("Saldo Demo", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("PNL Acumulado", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # Gráfico dinámico
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=2)))
            for o in st.session_state.ordenes_malla:
                color = "green" if o['estado'] == 'EJECUTADA' else "grey"
                fig.add_hline(y=o['precio'], line_dash="dash", line_color=color)
            if st.session_state.posiciones:
                fig.add_hline(y=p_tp, line_color="#00FFFF", annotation_text="Profit Target")
            fig.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=10))
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a: st.subheader("📋 Malla Actual"); st.table(st.session_state.ordenes_malla)
            with col_b: st.subheader("📜 Historial de Cierres"); st.table(st.session_state.historial_pnl)

            time.sleep(1); st.rerun()
        except: time.sleep(1); st.rerun()
            
