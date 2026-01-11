import streamlit as st
import pandas as pd
import requests
import time
import os
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Master Grid Futuros Pro", layout="wide")

# Estilo Trading Profesional
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    div[data-testid="stSidebar"] { background-color: #1E2329 !important; }
    h1, h2, h3, p, span, label { color: #EAECEF !important; }
    div[data-testid="metric-container"] { 
        background-color: #2B3139; border: 1px solid #474D57; border-radius: 8px;
    }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE SESIÓN (PROTEGIDA) ---
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

# Botón de Emergencia en el Sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🚨 CIERRE TOTAL DE EMERGENCIA", type="primary"):
    # Lógica de cierre total
    for pos in st.session_state.posiciones:
        st.session_state.saldo_demo += 2.0 # Recuperar margen base (ejemplo)
    st.session_state.posiciones = []
    st.sidebar.warning("⚠️ Todas las posiciones han sido cerradas.")
    st.rerun()

with st.sidebar.expander("🔑 API KEYS (Solo Real)"):
    st.text_input("API Key", type="password")
    st.text_input("Secret Key", type="password")

st.sidebar.markdown("---")
par = st.sidebar.selectbox("Moneda:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("Apalancamiento", 1, 50, 20)
monto_nivel = st.sidebar.number_input("Margen por Nivel (USDT)", value=5.0)

st.sidebar.subheader("📐 AJUSTE DE REJILLA")
dist_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.1, 2.0, 0.5) / 100
max_niveles = st.sidebar.slider("Máximo de niveles", 1, 15, 6)

bot_on = st.sidebar.toggle("⚡ ENCENDER ALGORITMO")

# --- LÓGICA DE PRECIO ---
def obtener_precio(symbol):
    try:
        coin = symbol.split("/")[0]
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD", timeout=5).json()
        return float(res['USD'])
    except:
        return st.session_state.precios_hist[-1] if st.session_state.precios_hist else 137.0

# --- UI PRINCIPAL ---
st.title(f"BOT GRID: {par} {leverage}x")

if bot_on:
    try:
        precio = obtener_precio(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # RSI Simulado (30-60)
        rsi = 28 + (precio % 1 * 45) 

        # --- LÓGICA DE TRADING (CORREGIDA) ---
        evento = "VIGILANDO"
        pnl_realizado = 0.0

        # 1. Compra N1
        if not st.session_state.posiciones and rsi <= 35:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto_nivel
            evento = "🛒 COMPRA N1"

        # 2. Rejilla
        elif 0 < len(st.session_state.posiciones) < max_niveles:
            ultimo_p = st.session_state.posiciones[-1]['precio']
            if precio <= ultimo_p * (1 - dist_grid):
                nuevo_id = len(st.session_state.posiciones) + 1
                st.session_state.posiciones.append({'precio': precio, 'id': nuevo_id})
                if not es_real: st.session_state.saldo_demo -= monto_nivel
                evento = f"🛒 COMPRA N{nuevo_id}"

        # 3. Venta (Con protección de 'id')
        indices_a_borrar = []
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            # Regla de oro: Cierra si llega al profit o RSI > 60 (siempre que el precio sea mayor)
            if (precio >= target or rsi >= 60) and precio > pos['precio']:
                pnl_realizado = ((precio - pos['precio']) / pos['precio']) * leverage * monto_nivel
                if not es_real:
                    st.session_state.saldo_demo += (monto_nivel + pnl_realizado)
                
                evento = f"💰 VENTA N{pos.get('id', 'N/A')}" # Uso seguro de .get()
                indices_a_borrar.append(i)
                
                # Registrar log
                new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": evento, "Precio": precio, "PNL": f"${pnl_realizado:.2f}", "Modo": modo}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                break # Evitar conflicto en el mismo ciclo

        for index in indices_a_borrar:
            if index < len(st.session_state.posiciones):
                st.session_state.posiciones.pop(index)

        # --- DASHBOARD ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("RSI", f"{rsi:.1f}")
        c3.metric("NIVELES", len(st.session_state.posiciones))
        c4.metric("BILLETERA", f"${st.session_state.saldo_demo:,.2f}")

        # --- GRÁFICO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=2), name="Precio"))
        
        for p in st.session_state.posiciones:
            # Línea de compra
            fig.add_hline(y=p['precio'], line_color="white", annotation_text=f"L{p.get('id')} Compra")
            # Línea de profit
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="gold", line_dash="dash", annotation_text="Profit")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, yaxis=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)
        time.sleep(2)
        st.rerun()

    except Exception as e:
        # Silenciar errores técnicos de refresco para no mostrar la pantalla roja
        st.info(f"Actualizando datos... ({e})")
        time.sleep(2)
        st.rerun()
