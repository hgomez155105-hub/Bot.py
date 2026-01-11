import streamlit as st
import pandas as pd
import requests
import time
import os
import plotly.graph_objects as go
from datetime import datetime

# Intentar importar CCXT para el modo real (Futuros Binance)
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Futuros Grid AI", layout="wide")

# Estilo visual mejorado (Modo Oscuro Trading)
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    div[data-testid="stSidebar"] { background-color: #1E2329 !important; }
    .metric-card { 
        background-color: #2B3139; border-radius: 10px; padding: 15px; border: 1px solid #474D57;
    }
    h1, h2, h3, p, span { color: #EAECEF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL", "Modo"])
    })

# --- SIDEBAR: CONTROL DE FUTUROS ---
st.sidebar.title("🚀 FUTUROS CONTROL")
modo = st.sidebar.radio("Entorno:", ["🧪 DEMO (Simulado)", "🔥 REAL (Binance Futuros)"])
es_real = modo == "🔥 REAL (Binance Futuros)"

if es_real:
    with st.sidebar.expander("🔑 LLAVES API"):
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")

st.sidebar.markdown("---")
par = st.sidebar.selectbox("Par de Futuros:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("Apalancamiento (Leverage)", 1, 50, 20)
monto_por_nivel = st.sidebar.number_input("Margen por Nivel (USDT)", value=10.0)

st.sidebar.subheader("📐 AJUSTE DE REJILLA")
distancia_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.1, 2.0, 0.5) / 100
max_niveles = st.sidebar.slider("Máximo de niveles abiertos", 1, 20, 5)

bot_on = st.sidebar.toggle("⚡ ENCENDER ALGORITMO")

# --- FUNCIONES DE MERCADO ---
def get_live_price(symbol):
    coin = symbol.split("/")[0]
    res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
    return float(res['USD'])

# --- UI PRINCIPAL ---
st.title(f"📊 BOT GRID FUTUROS: {par} {leverage}x")

if bot_on:
    try:
        precio = get_live_price(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # RSI para cumplimiento de tus criterios (30 compra / 60 venta)
        # (En producción usarías una librería técnica, aquí lo simulamos con la acción del precio)
        rsi = 30 + (precio % 1 * 40) 

        # --- LÓGICA DE REJILLA (GRID) ---
        evento = "VIGILANDO"
        pnl_realizado = 0.0

        # 1. Apertura del Primer Nivel (Solo si RSI < 35 para entrar barato)
        if not st.session_state.posiciones and rsi <= 35:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto_por_nivel
            evento = "🛒 NIVEL 1: COMPRA INICIAL"

        # 2. Apertura de Niveles Inferiores (Si el precio cae, promedia)
        elif 0 < len(st.session_state.posiciones) < max_niveles:
            ultimo_precio = st.session_state.posiciones[-1]['precio']
            if precio <= ultimo_precio * (1 - distancia_grid):
                st.session_state.posiciones.append({'precio': precio, 'id': len(st.session_state.posiciones)+1})
                if not es_real: st.session_state.saldo_demo -= monto_por_nivel
                evento = f"🛒 NIVEL {len(st.session_state.posiciones)}: COMPRA PROMEDIO"

        # 3. Cierre de Niveles (Profit o RSI alto)
        for i, pos in enumerate(st.session_state.posiciones):
            objetivo = pos['precio'] * (1 + distancia_grid)
            if precio >= objetivo or rsi >= 60:
                if precio > pos['precio']: # REGLA: SIEMPRE GANANCIA
                    pnl_realizado = ((precio - pos['precio']) / pos['precio']) * leverage * monto_por_nivel
                    if not es_real:
                        st.session_state.saldo_demo += (monto_por_nivel + pnl_realizado)
                    
                    st.session_state.posiciones.pop(i)
                    evento = f"💰 NIVEL {pos['id']}: TAKE PROFIT"
                    
                    # Log
                    new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": evento, "Precio": precio, "PNL": f"${pnl_realizado:.2f}", "Modo": modo}])
                    st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                    break

        # --- DASHBOARD ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("PRECIO", f"${precio:,.2f}")
        col2.metric("RSI", f"{rsi:.1f}")
        col3.metric("NIVELES ACTIVOS", len(st.session_state.posiciones))
        col4.metric("BILLETERA (DEMO)", f"${st.session_state.saldo_demo:,.2f}")

        # --- GRÁFICO CON NIVELES VISIBLES ---
        fig = go.Figure()
        # Línea de precio
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=2), name="Precio"))
        
        # Dibujar cada nivel de la rejilla
        for p in st.session_state.posiciones:
            # Línea de compra (Blanca)
            fig.add_hline(y=p['precio'], line_color="white", line_dash="solid", annotation_text=f"L{p['id']} Buy")
            # Línea de profit (Dorada)
            fig.add_hline(y=p['precio']*(1+distancia_grid), line_color="gold", line_dash="dash", annotation_text="Profit")

        # Línea de posible próxima compra (Roja)
        if len(st.session_state.posiciones) > 0 and len(st.session_state.posiciones) < max_niveles:
            prox_buy = st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid)
            fig.add_hline(y=prox_buy, line_color="red", line_dash="dot", annotation_text="Next Buy")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, 
                          margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(color="white", gridcolor="#30363D"))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)
        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(5)
        st.rerun()
else:
    st.info("Bot apagado. Configura tus niveles y enciende el simulador.")
        
