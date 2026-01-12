import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

# --- ESTADOS DEL BOT ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
        'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': ""
    })

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 Usuario Pro")
    st.divider()
    modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
    
    st.subheader("🔑 APIs de Exchange")
    st.text_input("Binance API Key", type="password")
    st.text_input("Binance Secret Key", type="password")
    
    st.subheader("📊 Configuración")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT"])
    
    if par != st.session_state.ultimo_par:
        st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
        st.rerun()

    lev = st.slider("Apalancamiento", 1, 50, 20)
    niveles = st.number_input("Cantidad de Órdenes", 1, 15, 5)
    distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0.5) / 100
    inversion_total = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
    
    st.subheader("🛡️ Resguardo RSI")
    rsi_compra = st.slider("RSI Compra (Bajo)", 10, 50, 36)
    rsi_venta = st.slider("RSI Venta (Alto)", 50, 90, 64)
    tp_global = st.slider("Take Profit (%)", 0.1, 10.0, 1.0) / 100

# --- LÓGICA DE TRADING ---
st.title(f"Ejecución: {par}")
bot_on = st.toggle("ACTIVAR ALGORITMO")

if bot_on:
    try:
        coin = par.split('/')[0]
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
        precio_act = float(res['USD'])
        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
        rsi_val = calcular_rsi(st.session_state.precios_hist)

        # 1. Crear Malla (Solo si no hay órdenes)
        if not st.session_state.ordenes_malla:
            monto_por_nivel = inversion_total / niveles
            for i in range(niveles):
                p_n = precio_act * (1 - (i * distancia))
                st.session_state.ordenes_malla.append({
                    'id': i+1, 'precio': round(p_n, 4), 
                    'monto': round(monto_por_nivel, 2), 'estado': 'PENDIENTE'
                })

        # 2. Ejecutar y Descontar (CORREGIDO)
        for o in st.session_state.ordenes_malla:
            if o['estado'] == 'PENDIENTE' and precio_act <= o['precio']:
                if st.session_state.saldo_demo >= o['monto']:
                    st.session_state.saldo_demo -= o['monto'] # Descuento exacto
                    o['estado'] = 'EJECUTADA'
                    st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})
                    st.toast(f"Comprado Nivel {o['id']} a ${precio_act}")

        # 3. Venta y Ganancia
        if st.session_state.posiciones:
            p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
            p_tp = p_prom * (1 + tp_global)
            
            if precio_act >= p_tp and rsi_val >= rsi_venta:
                total_recuperado = sum(p['monto'] for p in st.session_state.posiciones)
                profit_neto = (total_recuperado * tp_global) * lev
                st.session_state.saldo_demo += (total_recuperado + profit_neto)
                st.session_state.ganancia_acumulada += profit_neto
                st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                st.balloons()
                st.rerun()

        # --- DASHBOARD ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Precio Actual", f"${precio_act:,.2f}")
        c2.metric("Balance Disponible", f"${st.session_state.saldo_demo:,.2f}")
        c3.metric("PNL Acumulado", f"${st.session_state.ganancia_acumulada:,.2f}", delta=f"RSI: {rsi_val:.1f}")

        # --- GRÁFICO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=2)))
        for o in st.session_state.ordenes_malla:
            color = "green" if o['estado'] == 'EJECUTADA' else "rgba(100,100,100,0.5)"
            fig.add_hline(y=o['precio'], line_dash="dash", line_color=color)
        if st.session_state.posiciones:
            fig.add_hline(y=p_tp, line_color="#00FFFF", annotation_text="TAKE PROFIT")
        fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=10))
        st.plotly_chart(fig, use_container_width=True)

        # --- NUEVA TABLA DE MONITOREO ---
        st.subheader("📋 Estado de la Malla")
        if st.session
