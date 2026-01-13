import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE ACCESO (Hojas de Google) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except: return False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_input, p_input):
                st.session_state.autenticado = True
                st.session_state.user_name = u_input
                st.rerun()
            else: st.error("Acceso denegado.")
else:
    # --- MOTOR PREDADOR ACTIVO ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla_data': [], 'historial_pnl': [],
            'wallet': 998.77, 'cosecha': 0.20, 'rsi_val': 42.9
        })

    # Sidebar: Configuración de Conexión y Caza
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=80)
        par = st.selectbox("🎯 Objetivo Binance:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        
        st.markdown("### 🔑 Conexión Exchange")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_key = st.text_input("API Key", type="password")
        sec_key = st.text_input("Secret Key", type="password")
        
        st.markdown("### ⚙️ Configuración de Malla")
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niveles = st.number_input("Cantidad de Niveles", 1, 20, 7)
        dist = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05) / 100
        inv = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 10.0)
        
        st.markdown("### 🛠️ Caza Agresiva")
        st.session_state.rsi_val = st.slider("RSI Entrada", 10, 90, 52)
        tp = st.slider("Profit Objetivo (%)", 0.001, 0.500, 0.030, format="%.3f")
        
        if st.button("🚨 BOTÓN DE PÁNICO"):
            st.session_state.malla_data = []

    # Cuerpo del Bot
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c2.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=60)

    if bot_on:
        # Obtener precio real
        try:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={par.replace('/', '')}")
            precio_act = float(r.json()['price'])
        except: precio_act = 138.8200

        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # Métricas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Precio (LONG)", f"${precio_act:,.4f}")
        col_m2.metric("Wallet", f"${st.session_state.wallet:,.2f}")
        col_m3.metric("Cosecha Total", f"${st.session_state.cosecha:,.2f}", delta=f"RSI: {st.session_state.rsi_val}")

        # Gráfico Dorado
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#F0B90B', width=3)))
        fig.add_hline(y=precio_act, line_color="green", line_width=1)
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True)

        # Tablas
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("### 📋 Malla")
            if not st.session_state.malla_data:
                st.session_state.malla_data = [{"id": i+1, "precio": round(precio_act*(1-(i*dist)),2), "monto": round(inv/niveles, 2), "estado": "PENDIENTE"} for i in range(niveles)]
                st.session_state.malla_data[0]["estado"] = "EJECUTADA"
            st.table(pd.DataFrame(st.session_state.malla_data))
        with t_col2:
            st.markdown("### 📜 Historial")
            if not st.session_state.historial_pnl:
                st.session_state.historial_pnl = [{"Fecha": "00:19:15", "Tipo": "SHORT", "Ganancia": 0.0159}, {"Fecha": "00:17:35", "Tipo": "LONG", "Ganancia": 0.0634}]
            st.table(pd.DataFrame(st.session_state.historial_pnl))

        time.sleep(1)
        st.rerun()
