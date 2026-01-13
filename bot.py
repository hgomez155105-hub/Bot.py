import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 🔐 SISTEMA DE LOGIN (SE MANTIENE INTACTO) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(u, p):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str).str.strip() == str(u).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(p).strip())]
        return not match.empty
    except: return False

# --- 🎨 ESTILO Y CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE NAVEGACIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    # Pantalla de Login Limpia
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        st.title("Acceso al Sistema")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA"):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                st.rerun()
            else: st.error("Credenciales incorrectas.")
else:
    # --- 🏎️ MOTOR PREDADOR (REPARADO SEGÚN TU IMAGEN) ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla_data': [], 'historial_pnl': [],
            'wallet': 1000.0, 'cosecha': 0.0, 'rsi': 52.0
        })

    # Header Limpio (Sin el cuadro de login a la derecha)
    c_h1, c_h2 = st.columns([4, 1])
    with c_h1:
        st.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    with c_h2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=70)

    # Sidebar: Configuración (Como en la foto 1000266133.jpg)
    with st.sidebar:
        par = st.selectbox("🎯 Objetivo Binance:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        st.divider()
        st.markdown("### ⚙️ Configuración de Malla")
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niveles = st.number_input("Cantidad de Niveles", 1, 20, 7)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 10.0)
        st.divider()
        st.markdown("### 🛠️ Caza Agresiva")
        st.session_state.rsi = st.slider("RSI Entrada", 10, 90, 52)
        tp = st.slider("Profit Objetivo (%)", 0.01, 0.5, 0.03)
        if st.button("🚨 BOTÓN DE PÁNICO"):
            st.session_state.malla_data = []; st.warning("Malla Cerrada")

    if bot_on:
        # Captura de Motor Real
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={par.replace('/', '')}"
            precio_act = float(requests.get(url).json()['price'])
        except: precio_act = 138.82

        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # --- 📊 ZONA DE MÉTRICAS (COSECHA INCLUIDA) ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Precio (LONG)", f"${precio_act:,.4f}")
        m2.metric("Wallet", f"${st.session_state.wallet:,.2f}")
        m3.metric("Cosecha Total", f"${st.session_state.cosecha:,.2f}", delta=f"RSI: {st.session_state.rsi}")

        # Gráfico Predador
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#F0B90B', width=3)))
        fig.add_hline(y=precio_act, line_dash="dash", line_color="green")
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True)

        # --- 📋 TABLAS INFERIORES (REPARADAS) ---
        t1, t2 = st.columns(2)
        with t1:
            st.markdown("### 📋 Malla Activa")
            if not st.session_state.malla_data:
                st.session_state.malla_data = [{"id": i+1, "precio": round(precio_act*(1-(i*distancia)),2), "monto": round(inversion/niveles, 2), "estado": "PENDIENTE"} for i in range(niveles)]
                st.session_state.malla_data[0]["estado"] = "EJECUTADA"
            st.table(pd.DataFrame(st.session_state.malla_data))

        with t2:
            st.markdown("### 📜 Historial PNL")
            if not st.session_state.historial_pnl:
                st.session_state.historial_pnl = [{"Fecha": datetime.now().strftime("%H:%M:%S"), "Tipo": "SHORT", "Ganancia": 0.0159}]
            st.table(pd.DataFrame(st.session_state.historial_pnl))

        time.sleep(1)
        st.rerun()
