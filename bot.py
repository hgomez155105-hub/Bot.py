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

# --- SESIÓN Y LOGIN (Simulado para que no falle) ---
if 'user_name' not in st.session_state:
    st.session_state.user_name = "Usuario Pro"

# --- ESTADOS DEL BOT ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
        'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': ""
    })

# --- SIDEBAR COMPLETO ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_name}")
    st.divider()
    
    modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
    
    st.subheader("🔑 APIs de Exchange")
    api_key = st.text_input("Binance API Key", type="password")
    api_secret = st.text_input("Binance Secret Key", type="password")
    
    st.subheader("📊 Estrategia de Malla")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT"])
    
    # RESET AL CAMBIAR MONEDA
    if par != st.session_state.ultimo_par:
        st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
        st.rerun()

    lev = st.slider("Apalancamiento", 1, 50, 20)
    niveles = st.number_input("Cantidad de Órdenes", 1, 15, 5)
    distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0.5) / 100
    inversion = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
    
    st.subheader("🛡️ Resguardo RSI")
    rsi_compra = st.slider("RSI Compra (Bajo)", 10, 50, 30)
    rsi_venta = st.slider("RSI Venta (Alto)", 50, 90, 70)
    tp_global = st.slider("Take Profit Global (%)", 0.1, 5.0, 0.5) / 100

# --- PANEL DE CONTROL ---
st.title(f"Ejecución: {par} ({modo})")
bot_on = st.toggle("ACTIVAR ALGORITMO")

if bot_on:
    try:
        # Obtener Precio
        coin = par.split('/')[0]
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        rsi_act = calcular_rsi(st.session_state.precios_hist)

        # Crear malla si no existe
        if not st.session_state.ordenes_malla:
            m_nivel = inversion / niveles
            for i in range(niveles):
                p_n = precio * (1 - (i * distancia))
                st.session_state.ordenes_malla.append({'precio': p_n, 'monto': m_nivel, 'estado': 'pendiente'})

        # Ejecución y descuento de saldo
        for o in st.session_state.ordenes_malla:
            if o['estado'] == 'pendiente' and precio <= o['precio']:
                if st.session_state.saldo_demo >= o['monto']:
                    o['estado'] = 'ejecutada'
                    st.session_state.posiciones.append({'entrada': precio, 'monto': o['monto']})
                    st.session_state.saldo_demo -= o['monto']
                    st.toast(f"Compra en {precio}")

        # Lógica de Venta (Con filtro RSI de venta)
        if st.session_state.posiciones:
            p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
            p_tp = p_prom * (1 + tp_global)
            
            # Solo vende si llega al precio Y el RSI es mayor al rsi_venta configurado
            if precio >= p_tp and rsi_act >= rsi_venta:
                total_m = sum(p['monto'] for p in st.session_state.posiciones)
                pnl = (total_m * tp_global) * lev
                st.session_state.saldo_demo += (total_m + pnl)
                st.session_state.ganancia_acumulada += pnl
                st.session_state.posiciones = []
                st.session_state.ordenes_malla = []
                st.balloons()
                st.rerun()

        # DASHBOARD
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Precio {coin}", f"${precio:,.2f}")
        c2.metric("Disponible (DEMO)", f"${st.session_state.saldo_demo:,.2f}")
        c3.metric("PNL Total", f"${st.session_state.ganancia_acumulada:,.2f}", delta=f"RSI: {rsi_act:.1f}")

        # --- GRÁFICO RECONSTRUIDO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name="Precio", line=dict(color='#F0B90B', width=2)))

        # Dibujar malla
        for orden in st.session_state.ordenes_malla:
            color = "green" if orden['estado'] == 'ejecutada' else "rgba(150,150,150,0.5)"
            fig.add_hline(y=orden['precio'], line_dash="dash", line_color=color, annotation_text=" NIVEL COMPRA")

        # Dibujar línea de profit si hay posiciones
        if st.session_state.posiciones:
            p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
            fig.add_hline(y=p_prom * (1 + tp_global), line_color="#00FFFF", line_width=2, annotation_text=" TAKE PROFIT")

        fig.update_layout(height=500, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=20))
        st.plotly_chart(fig, use_container_width=True)

        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(2)
        st.rerun()
            
