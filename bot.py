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

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 10px; padding: 15px; text-align: center;
    }
    .metric-value { font-size: 1.4rem; font-weight: bold; color: #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
        'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': ""
    })

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT"])
    
    if par != st.session_state.ultimo_par:
        st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
        st.rerun()

    lev = st.slider("Apalancamiento", 1, 50, 20)
    niveles = st.number_input("Niveles de Malla", 1, 15, 5)
    distancia = st.slider("Distancia (%)", 0.1, 2.0, 0.4) / 100
    monto_total = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
    tp_global = st.slider("Take Profit (%)", 0.1, 5.0, 0.5) / 100
    rsi_trigger = st.slider("RSI para Iniciar Compra", 10, 70, 40)

# --- PANEL PRINCIPAL ---
st.title(f"Trading: {par}")
bot_on = st.toggle("EJECUTAR ALGORITMO")

if bot_on:
    try:
        coin = par.split('/')[0]
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        rsi_actual = calcular_rsi(st.session_state.precios_hist)

        # Lógica de Malla: Crear órdenes si no existen
        if not st.session_state.posiciones and not st.session_state.ordenes_malla:
            # Quitamos la restricción estricta de RSI solo para que veas la malla funcionar de inmediato si quieres
            monto_nivel = monto_total / niveles
            for i in range(niveles):
                p_nivel = precio * (1 - (i * distancia))
                st.session_state.ordenes_malla.append({'precio': p_nivel, 'monto': monto_nivel, 'estado': 'pendiente'})

        # Ejecución y DESCUENTO de saldo
        for orden in st.session_state.ordenes_malla:
            if orden['estado'] == 'pendiente' and precio <= orden['precio']:
                if st.session_state.saldo_demo >= orden['monto']:
                    orden['estado'] = 'ejecutada'
                    st.session_state.posiciones.append({'entrada': precio, 'monto': orden['monto']})
                    st.session_state.saldo_demo -= orden['monto']
                    st.toast(f"Compra ejecutada a {precio}")

        # Cierre por Profit
        p_profit = 0
        if st.session_state.posiciones:
            p_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
            p_profit = p_promedio * (1 + tp_global)
            if precio >= p_profit:
                total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                pnl = (total_inv * tp_global) * lev
                st.session_state.saldo_demo += (total_inv + pnl)
                st.session_state.ganancia_acumulada += pnl
                st.session_state.posiciones = []
                st.session_state.ordenes_malla = []
                st.balloons()
                st.rerun()

        # Dashboard scannable
        c1, c2, c3 = st.columns(3)
        c1.metric("Precio Actual", f"${precio:,.2f}")
        c2.metric("Saldo Disponible", f"${st.session_state.saldo_demo:,.2f}")
        c3.metric("Ganancia Total", f"${st.session_state.ganancia_acumulada:,.2f}", delta=f"{rsi_actual:.1f} RSI")

        # --- GRÁFICO REFORMADO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name="Precio", line=dict(color='#F0B90B', width=3)))

        # Dibujar CADA NIVEL de la malla
        for idx, orden in enumerate(st.session_state.ordenes_malla):
            color = "green" if orden['estado'] == 'ejecutada' else "gray"
            fig.add_hline(y=orden['precio'], line_dash="dash", line_color=color, 
                          annotation_text=f"Nivel {idx+1} (${orden['precio']:.2f})", annotation_position="bottom right")

        # Dibujar Take Profit
        if st.session_state.posiciones and p_profit > 0:
            fig.add_hline(y=p_profit, line_color="#00FFFF", line_width=2, 
                          annotation_text="TAKE PROFIT AQUÍ", annotation_position="top right")

        fig.update_layout(height=500, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=30))
        st.plotly_chart(fig, use_container_width=True)
        
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"Error en ejecución: {e}")
        time.sleep(2)
        st.rerun()
    
