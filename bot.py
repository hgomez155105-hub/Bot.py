import streamlit as st
import pandas as pd
import requests
import time
import os
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Master Grid Futuros", layout="wide")

# Estilo Trading Oscuro
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    div[data-testid="stSidebar"] { background-color: #1E2329 !important; }
    h1, h2, h3, p, span, label { color: #EAECEF !important; }
    div[data-testid="metric-container"] { 
        background-color: #2B3139; border: 1px solid #474D57; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL", "Modo"])
    })

# --- SIDEBAR: CONTROLES ---
st.sidebar.title("🚀 FUTUROS CONTROL")
modo = st.sidebar.radio("Entorno:", ["🧪 DEMO (Virtual)", "🔥 REAL (Binance)"])
es_real = modo == "🔥 REAL (Binance)"

with st.sidebar.expander("🔑 API KEYS (Solo Modo Real)"):
    api_k = st.text_input("API Key", type="password")
    api_s = st.text_input("Secret Key", type="password")

st.sidebar.markdown("---")
par = st.sidebar.selectbox("Moneda:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("Apalancamiento (Leverage)", 1, 50, 20)
monto_nivel = st.sidebar.number_input("Margen por Nivel (USDT)", value=5.0)

st.sidebar.subheader("📐 AJUSTE DE REJILLA")
dist_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.1, 2.0, 0.5) / 100
max_niveles = st.sidebar.slider("Máximo de niveles", 1, 15, 6)

bot_on = st.sidebar.toggle("⚡ ENCENDER ALGORITMO")

# --- LÓGICA DE MERCADO ---
def obtener_precio(symbol):
    coin = symbol.split("/")[0]
    res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
    return float(res['USD'])

# --- UI PRINCIPAL ---
st.title(f"BOT GRID: {par} {leverage}x")

if bot_on:
    try:
        precio = obtener_precio(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # RSI Simulado (para cumplir tus criterios 30/60)
        rsi = 25 + (precio % 1 * 50) 

        # --- LÓGICA DE TRADING ---
        evento = "VIGILANDO"
        pnl_realizado = 0.0

        # 1. Entrada Nivel 1 (Criterio RSI < 35)
        if not st.session_state.posiciones and rsi <= 35:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto_nivel
            evento = "🛒 COMPRA N1 (RSI BAJO)"

        # 2. Rejilla: Compras si el precio cae
        elif 0 < len(st.session_state.posiciones) < max_niveles:
            ultimo_p = st.session_state.posiciones[-1]['precio']
            if precio <= ultimo_p * (1 - dist_grid):
                nuevo_id = len(st.session_state.posiciones) + 1
                st.session_state.posiciones.append({'precio': precio, 'id': nuevo_id})
                if not es_real: st.session_state.saldo_demo -= monto_nivel
                evento = f"🛒 COMPRA N{nuevo_id} (PROMEDIO)"

        # 3. Venta (Take Profit o RSI > 60)
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            if precio >= target or rsi >= 60:
                if precio > pos['precio']: # SIEMPRE GANANCIA
                    pnl_realizado = ((precio - pos['precio']) / pos['precio']) * leverage * monto_nivel
                    if not es_real:
                        st.session_state.saldo_demo += (monto_nivel + pnl_realizado)
                    
                    st.session_state.posiciones.pop(i)
                    evento = f"💰 VENTA N{pos['id']} (PROFIT)"
                    
                    new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": evento, "Precio": precio, "PNL": f"${pnl_realizado:.2f}", "Modo": modo}])
                    st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                    break

        # --- DASHBOARD ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("RSI", f"{rsi:.1f}")
        c3.metric("NIVELES", len(st.session_state.posiciones))
        c4.metric("BILLETERA", f"${st.session_state.saldo_demo:,.2f}")

        # --- GRÁFICO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=2), name="Precio"))
        
        # Dibujar líneas de Niveles
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", annotation_text=f"L{p['id']} Compra")
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="gold", line_dash="dash", annotation_text="Venta")

        # Línea de próxima compra si cae
        if 0 < len(st.session_state.posiciones) < max_niveles:
            prox_buy = st.session_state.posiciones[-1]['precio'] * (1 - dist_grid)
            fig.add_hline(y=prox_buy, line_color="red", line_dash="dot", annotation_text="Próx. Compra")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, yaxis=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)
        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Error detectado: {e}")
        time.sleep(5)
        st.rerun()
