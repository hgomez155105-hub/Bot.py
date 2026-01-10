import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Grid Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 1px solid #FFFFFF; border-radius: 10px; padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA ---
if 'moneda_activa' not in st.session_state:
    st.session_state.moneda_activa = "BTC"

# Esta función es la que evita el error que mencionas
def limpiar_memoria_por_cambio():
    st.session_state.precios_hist = []
    st.session_state.posiciones = []
    st.session_state.x_est = 0.0
    st.session_state.p_cov = 1.0
    # No borramos la ganancia acumulada para que veas cuánto vas ganando en total

if 'log_df' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 
        'ganancia_acumulada': 0.0,
        'precios_hist': [], 
        'posiciones': [], 
        'x_est': 0.0, 
        'p_cov': 1.0,
        'log_df': pd.DataFrame(columns=["Hora", "Moneda", "Evento", "Precio", "PNL Nivel"])
    })

# --- SIDEBAR ---
st.sidebar.header("🕹️ CONTROL DE GRID")
nueva_moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "XRP", "ADA"])

# Detectar cambio de moneda para evitar cierres falsos
if nueva_moneda != st.session_state.moneda_activa:
    st.session_state.moneda_activa = nueva_moneda
    limpiar_memoria_por_cambio()
    st.rerun()

apalancamiento = st.sidebar.slider("Apalancamiento (Leverage):", 1, 50, 10)
monto_por_nivel = st.sidebar.number_input("Monto por Nivel (USD):", value=50.0)

st.sidebar.subheader("📐 PARÁMETROS DE REJILLA")
distancia_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.05, 2.0, 0.2) / 100
niveles_max = st.sidebar.slider("Máximo de niveles:", 1, 20, 7)

encendido = st.sidebar.toggle("🚀 ENCENDER ALGORITMO", key="bot_activo")

# --- UI PRINCIPAL ---
st.title(f"📊 GRID BOT: {st.session_state.moneda_activa}")

if st.session_state.bot_activo:
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={st.session_state.moneda_activa}&tsyms=USD"
        precio = float(requests.get(url, timeout=5).json()['USD'])
        
        # IA Kalman
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        R, Q = 0.01**2, 0.001**2
        cov_prior = st.session_state.p_cov + Q
        ganancia_k = cov_prior / (cov_prior + R)
        st.session_state.x_est += ganancia_k * (precio - st.session_state.x_est)
        st.session_state.p_cov = (1 - ganancia_k) * cov_prior
        
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # LÓGICA DE GRID
        evento = "VIGILANDO"
        pnl_trade = 0.0
        
        # Abrir primer nivel
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'monto': monto_por_nivel, 'id': 1})
            st.session_state.saldo -= monto_por_nivel
            evento = "🛒 NIVEL 1 OPEN"
        
        # Niveles inferiores
        elif len(st.session_state.posiciones) < niveles_max:
            if precio <= st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid):
                st.session_state.posiciones.append({'precio': precio, 'monto': monto_por_nivel, 'id': len(st.session_state.posiciones)+1})
                st.session_state.saldo -= monto_por_nivel
                evento = f"🛒 NIVEL {len(st.session_state.posiciones)} OPEN"

        # Cierre por profit
        for i, pos in enumerate(st.session_state.posiciones):
            dif = (precio - pos['precio']) / pos['precio']
            if dif >= distancia_grid:
                pnl_trade = (dif * apalancamiento) * pos['monto']
                st.session_state.saldo += (pos['monto'] + pnl_trade)
                st.session_state.ganancia_acumulada += pnl_trade
                st.session_state.posiciones.pop(i)
                evento = f"💰 NIVEL {pos['id']} PROFIT"
                break

        # DASHBOARD
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("GANANCIA ACUM.", f"${st.session_state.ganancia_acumulada:.2f}")
        c3.metric("CASH", f"${st.session_state.saldo:,.2f}")

        # GRÁFICO
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', name='Precio', line=dict(color='#00FF00')))
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_dash="solid", line_color="white")
            fig.add_hline(y=p['precio']*(1+distancia_grid), line_dash="dash", line_color="gold")
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # LOG
        hora = datetime.now().strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Moneda": st.session_state.moneda_activa, "Evento": evento, "Precio": f"${precio:,.2f}", "PNL Nivel": f"${pnl_trade:.2f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
        st.dataframe(st.session_state.log_df.head(15), use_container_width=True)

        time.sleep(4)
        st.rerun()

    except Exception as e:
        st.warning("Conectando...")
        time.sleep(2)
        st.rerun()
            
