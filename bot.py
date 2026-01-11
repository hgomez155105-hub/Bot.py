import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Elite", layout="centered")

# --- ESTILO MÓVIL (MANTENIDO) ---
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
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN RSI (Trabajando en el motor interno) ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50.0
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_ganancia = np.mean(ganancias[-periodo:])
    avg_perdida = np.mean(perdidas[-periodo:])
    if avg_perdida == 0: return 100.0
    rs = avg_ganancia / avg_perdida
    return 100.0 - (100.0 / (1+rs))

# --- INICIALIZACIÓN ---
if 'ganancia_acumulada' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'saldo_real': 0.0,
        'ganancia_acumulada': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- BARRA LATERAL (AJUSTES) ---
with st.sidebar:
    st.markdown("### 🎮 CONTROL CENTRAL")
    modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL (BINANCE)"])
    es_real = modo == "⚡ MODO REAL (BINANCE)"
    
    if es_real:
        with st.expander("🔑 API KEYS", expanded=True):
            api_key = st.text_input("API Key", type="password")
            api_secret = st.text_input("Secret Key", type="password")
            st.session_state.saldo_real = 500.0 

    st.markdown("---")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
    leverage = st.slider("Apalancamiento (x)", 1, 50, 25)
    monto = st.number_input("Inversión (USDT)", value=2.0)
    dist_grid = st.slider("Profit Objetivo (%)", 0.05, 1.0, 0.1) / 100
    dist_recompra = 0.5 / 100 

    if st.button("🚨 RESET TOTAL", type="primary"):
        st.session_state.posiciones = []
        st.session_state.ganancia_acumulada = 0.0
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.markdown(f"<h3 style='text-align: center; color: white;'>🚀 {modo}</h3>", unsafe_allow_html=True)
bot_on = st.toggle("ENCENDER ALGORITMO")

if bot_on:
    try:
        # Obtención de datos
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)
        rsi_val = calcular_rsi(st.session_state.precios_hist)

        # 1. ENTRADA INICIAL
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto
            else: st.session_state.saldo_real -= monto

        # 2. RECOMPRA SI BAJA (Soporte de Grilla)
        else:
            ultima_pos = st.session_state.posiciones[-1]
            if precio <= ultima_pos['precio'] * (1 - dist_recompra):
                nuevo_id = len(st.session_state.posiciones) + 1
                st.session_state.posiciones.append({'precio': precio, 'id': nuevo_id})
                if not es_real: st.session_state.saldo_demo -= monto
                else: st.session_state.saldo_real -= monto

        # 3. CIERRE POR PROFIT O RSI ALTO
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            if (precio >= target or rsi_val >= 70) and precio > pos['precio']:
                pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto
                if not es_real: st.session_state.saldo_demo += (monto + pnl)
                else: st.session_state.saldo_real += (monto + pnl)
                
                st.session_state.ganancia_acumulada += pnl
                new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": f"PROFIT N{pos['id']}", "Precio": precio, "PNL": f"${pnl:.2f}"}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                st.session_state.posiciones.pop(i)
                st.rerun()

        # --- PANEL DE MÉTRICAS (PRECIO | BILLETERA | ACUMULADO) ---
        c1, c2, c3 = st.columns(3)
        v_billetera = st.session_state.saldo_real if es_real else st.session_state.saldo_demo
        l_billetera = "BILLETERA REAL" if es_real else "BILLETERA DEMO"

        with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>PRECIO</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>{l_billetera}</div><div class='metric-value' style='color:#F0B90B;'>${v_billetera:,.2f}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>ACUMULADO</div><div class='metric-value' style='color:#00FFAA;'>${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

        # --- GRÁFICO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00', width=2)))
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", line_width=1, annotation_text=f"N{p['id']} ENTRY")
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="#F0B90B", line_dash="dash", annotation_text="TARGET")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, 
                          margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(showgrid=False, color="gray", side="right"),
                          xaxis=dict(showgrid=False, showticklabels=False))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)
        time.sleep(2)
        st.rerun()

    except Exception:
        time.sleep(1)
        st.rerun()
            
