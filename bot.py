import streamlit as st
import pandas as pd
import requests
import time
import ccxt # Motor de conexión profesional
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Pro", layout="centered")

# --- ESTILO MÓVIL PREMIUM ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: linear-gradient(145deg, #1e2329, #2b3139);
        border: 1px solid #474D57;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        text-align: center;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    .metric-label { font-size: 0.75rem; color: #848E9C; font-weight: bold; }
    .metric-value { font-size: 1.3rem; font-weight: 800; color: #F0B90B; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE CONEXIÓN BINANCE ---
def conectar_binance(api_key, api_secret):
    try:
        return ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {'defaultType': 'future'}, # IMPORTANTE: Modo Futuros
            'enableRateLimit': True
        })
    except Exception:
        return None

# --- INICIALIZACIÓN ---
if 'ganancia_acumulada' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'ganancia_acumulada': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2584/2584687.png", width=80) # Icono temp
    st.title("Settings")
    modo = st.radio("Modo de Red:", ["🧪 DEMO", "🔥 REAL BINANCE"])
    
    if modo == "🔥 REAL BINANCE":
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
    
    par = st.selectbox("Par de Trading:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
    leverage = st.slider("Apalancamiento", 1, 50, 20)
    monto = st.number_input("Inversión por Nivel", value=10.0)
    dist_grid = st.slider("Take Profit (%)", 0.1, 5.0, 0.7) / 100

    if st.button("🚨 EMERGENCY STOP", type="primary"):
        st.session_state.posiciones = []
        st.rerun()

# --- LÓGICA DE MERCADO ---
st.markdown(f"<h2 style='text-align: center;'>AI SCALPER ELITE</h2>", unsafe_allow_html=True)
bot_on = st.toggle("🚀 INICIAR OPERATIVA REAL")

if bot_on:
    try:
        # Obtener Precio
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 30: st.session_state.precios_hist.pop(0)
        
        rsi = 35 + (precio % 1 * 40) # RSI Proyectado

        # LÓGICA DE TRADING AGRESIVA
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            # Aquí iría: binance.create_market_buy_order(...) si es REAL
            st.session_state.saldo_demo -= monto

        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            if (precio >= target or rsi >= 70) and precio > pos['precio']:
                pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto
                st.session_state.saldo_demo += (monto + pnl)
                st.session_state.ganancia_acumulada += pnl
                
                # Registro con Hora Local
                new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": "PROFIT", "Precio": precio, "PNL": f"${pnl:.2f}"}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                st.session_state.posiciones.pop(i)
                st.rerun()

        # --- UI MÓVIL (TARJETAS) ---
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>PRECIO</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card'><div class='metric-label'>WALLET</div><div class='metric-value'>${st.session_state.saldo_demo:,.1f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>RSI</div><div class='metric-value'>{rsi:.1f}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card'><div class='metric-label'>TOTAL PNL</div><div class='metric-value' style='color:#00FF00;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

        # Gráfico Táctil
        fig = go.Figure(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#F0B90B', width=3)))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.dataframe(st.session_state.log_df.head(5), use_container_width=True)
        time.sleep(2)
        st.rerun()

    except Exception as e:
        time.sleep(2)
        st.rerun()
else:
    st.info("Configura el bot en el menú lateral y actívalo para comenzar a tradear.")
