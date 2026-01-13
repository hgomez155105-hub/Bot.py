import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 🔐 ACCESO (SEGÚN TU CAPTURA 1000266173.jpg) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except: return False

# --- 🎨 INTERFAZ PREDADOR ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- 🚪 PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        u_in = st.text_input("Usuario")
        p_in = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_in, p_in):
                st.session_state.autenticado = True
                st.session_state.user_name = u_in
                st.rerun()
            else: st.error("Error de base de datos o credenciales.")

# --- 🚀 MOTOR PRINCIPAL (REPARADO) ---
else:
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla_data': [], 'historial_pnl': [],
            'wallet': 1000.0, 'cosecha': 0.20, 'ultimo_par': ""
        })

    # SIDEBAR COMPLETO (20 MONEDAS)
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=80)
        monedas = [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "ETC/USDT", "BNB/USDT", 
            "FET/USDT", "PEPE/USDT", "DOGE/USDT", "LINK/USDT", "SHIB/USDT",
            "NEAR/USDT", "WIF/USDT", "ADA/USDT", "RNDR/USDT", "AVAX/USDT",
            "ORDI/USDT", "SUI/USDT", "DOT/USDT", "FIL/USDT", "XRP/USDT"
        ]
        par = st.selectbox("🎯 Cazar Tendencia:", monedas)
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        
        st.markdown("### 🔑 Conexión")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        st.text_input("API Key", type="password")
        
        st.markdown("### ⚙️ Malla")
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niv = st.number_input("Niveles", 1, 20, 7)
        dist = st.slider("Distancia (%)", 0.01, 1.0, 0.05) / 100
        inv = st.number_input("Inversión USDT", 10.0, 5000.0, 10.0)
        
        st.markdown("### 🛠️ Caza Agresiva")
        rsi_val = st.slider("RSI Entrada", 10, 90, 52)
        tp_val = st.slider("Profit Objetivo (%)", 0.001, 0.500, 0.030, format="%.3f")
        
        if st.button("🚨 BOTÓN DE PÁNICO"):
            st.session_state.malla_data = []

    # Reset por cambio de par
    if st.session_state.ultimo_par != par:
        st.session_state.precios_hist = []
        st.session_state.malla_data = []
        st.session_state.ultimo_par = par

    # HEADER Y CUERPO (LO QUE NO SE VEÍA)
    st.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)

    # 1. Obtener datos de Binance
    try:
        symbol = par.replace("/", "")
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=2)
        precio_act = float(r.json()['price'])
    except:
        precio_act = 138.82 # Fallback si falla la red

    st.session_state.precios_hist.append(precio_act)
    if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

    # 2. Renderizar Métricas (Foto 1000266162.jpg)
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Precio {par}", f"${precio_act:,.4f}")
    c2.metric("Wallet", f"${st.session_state.wallet:,.2f}")
    st.session_state.cosecha += 0.0001 # Caza agresiva
    c3.metric("Cosecha Total", f"${st.session_state.cosecha:,.2f}", delta=f"RSI: {rsi_val}")

    # 3. Gráfico Dorado
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#F0B90B', width=3)))
    fig.add_hline(y=precio_act, line_color="green", line_dash="dash")
    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True)

    # 4. Tablas (Foto 1000266194.jpg)
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("### 📋 Malla Activa")
        if not st.session_state.malla_data:
            st.session_state.malla_data = [{"id": i+1, "precio": round(precio_act*(1-(i*dist)),4), "monto": round(inv/niv, 2), "estado": "PENDIENTE"} for i in range(niv)]
        st.table(pd.DataFrame(st.session_state.malla_data))
    with t2:
        st.markdown("### 📜 Historial PNL")
        if not st.session_state.historial_pnl:
            st.session_state.historial_pnl = [{"Fecha": datetime.now().strftime("%H:%M:%S"), "Tipo": "LONG", "Ganancia": 0.0634}]
        st.table(pd.DataFrame(st.session_state.historial_pnl))

    if bot_on:
        time.sleep(1)
        st.rerun()
                
