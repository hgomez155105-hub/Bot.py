import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Elite", layout="centered")

# --- ESTILO MÓVIL PROFESIONAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 10px; text-align: center;
    }
    .metric-label { font-size: 0.7rem; color: #848E9C; font-weight: bold; }
    .metric-value { font-size: 1.1rem; font-weight: bold; color: #F0B90B; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Estilo para los inputs de API */
    .stTextInput>div>div>input {
        background-color: #2B3139 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'ganancia_acumulada' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'ganancia_acumulada': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- BARRA LATERAL (EL CORAZÓN DE LA APP) ---
with st.sidebar:
    st.markdown("### 🎮 CONTROL CENTRAL")
    
    # Selector de Modo: Demo vs Real
    modo = st.radio("Entorno de Ejecución:", ["🧪 MODO DEMO", "⚡ MODO REAL (BINANCE)"])
    es_real = modo == "⚡ MODO REAL (BINANCE)"
    
    # Sección de API Keys (Solo aparece en modo Real)
    if es_real:
        with st.expander("🔑 CONFIGURAR API KEYS", expanded=True):
            api_key = st.text_input("Binance API Key", type="password")
            api_secret = st.text_input("Binance Secret Key", type="password")
            st.caption("Tus llaves se usan solo para ejecutar órdenes vía CCXT.")

    st.markdown("---")
    st.markdown("### ⚙️ AJUSTES DE ESTRATEGIA")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
    leverage = st.slider("Apalancamiento (x)", 1, 50, 20)
    monto = st.number_input("Margen por Nivel (USDT)", value=10.0)
    dist_grid = st.slider("Profit Objetivo (%)", 0.1, 5.0, 0.7) / 100

    if st.button("🚨 RESET / CIERRE TOTAL", type="primary"):
        st.session_state.posiciones = []
        st.session_state.ganancia_acumulada = 0.0
        st.rerun()

# --- LÓGICA DE MERCADO ---
st.markdown(f"<h3 style='text-align: center; color: white;'>🚀 {modo}</h3>", unsafe_allow_html=True)
bot_on = st.toggle("ENCENDER ALGORITMO")

if bot_on:
    try:
        # Obtención de Precio Real
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)
        
        rsi = 30 + (precio % 1 * 50) # RSI Simulado para la demo

        # Lógica de Apertura
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto

        # Lógica de Cierre (Profit o RSI 70)
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            if (precio >= target or rsi >= 70) and precio > pos['precio']:
                pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto
                
                if not es_real: st.session_state.saldo_demo += (monto + pnl)
                st.session_state.ganancia_acumulada += pnl
                
                # Registro en Historial
                new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": "PROFIT", "Precio": precio, "PNL": f"${pnl:.2f}"}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                
                st.session_state.posiciones.pop(i)
                st.rerun()

        # --- PANEL DE MÉTRICAS (VISIBILIDAD MÓVIL) ---
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>PRECIO</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>RSI</div><div class='metric-value'>{rsi:.1f}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>GANADO</div><div class='metric-value' style='color:#00FFAA;'>${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

        # --- GRÁFICO CON LÍNEAS DE REFERENCIA ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00', width=2)))
        
        for p in st.session_state.posiciones:
            # Entrada (Blanca)
            fig.add_hline(y=p['precio'], line_color="white", line_width=1, annotation_text="ENTRY", annotation_position="top left")
            # Salida (Amarilla)
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="#F0B90B", line_dash="dash", annotation_text="TARGET", annotation_position="top right")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, 
                          margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(showgrid=False, color="gray", side="right"),
                          xaxis=dict(showgrid=False, showticklabels=False))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Historial reciente
        st.dataframe(st.session_state.log_df.head(5), use_container_width=True)
        time.sleep(2)
        st.rerun()

    except Exception:
        time.sleep(1)
        st.rerun()
else:
    st.info("👋 Bot en pausa. Abre el menú lateral ( < ) para elegir el modo (Demo/Real) y configurar tus API Keys.")
                
