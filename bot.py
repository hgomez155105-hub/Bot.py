import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE BASE DE DATOS (LOGIN) ---
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
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    .stButton>button { width: 100%; background-color: #1E2329; color: white; border: 1px solid #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        st.title("H y G Inovaciones")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA"):
            if verificar_acceso(u, p):
                st.session_state.autenticado = True
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")
else:
    # --- MOTOR PREDADOR RESTAURADO (COMO EN TUS FOTOS) ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'precios_hist': [], 'malla': [], 'historial': [],
            'wallet': 1000.0, 'cosecha': 0.0
        })

    # Header con Logo y Usuario
    c_head1, c_head2 = st.columns([4, 1])
    c_head1.markdown(f"## 👁️ H y G Inovaciones - 👤 {st.session_state.user_name}")
    c_head2.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=60)

    # Sidebar: Configuración de Malla y Caza
    with st.sidebar:
        par = st.selectbox("🎯 Objetivo Binance:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        
        st.markdown("### ⚙️ Configuración de Malla")
        apalancamiento = st.slider("Apalancamiento", 1, 50, 22)
        niveles = st.number_input("Cantidad de Niveles", 1, 20, 7)
        distancia = st.slider("Distancia Malla (%)", 0.01, 1.0, 0.05) / 100
        inversion_total = st.number_input("Inversión Total (USDT)", 10.0, 1000.0, 10.0)

        st.markdown("### 🛠️ Caza Agresiva")
        rsi_entrada = st.slider("RSI Entrada", 10, 90, 52)
        take_profit = st.slider("Profit Objetivo (%)", 0.001, 0.5, 0.03, format="%.3f")

        if st.button("🚨 BOTÓN DE PÁNICO"):
            st.session_state.malla = []
            st.warning("Malla liquidada.")

    if bot_on:
        # Simulación de Motor de Precios (Reemplazar con API de Binance real si es REAL)
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={par.replace('/', '')}"
            precio_act = float(requests.get(url).json()['price'])
        except:
            precio_act = st.session_state.precios_hist[-1] if st.session_state.precios_hist else 138.82

        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # Métricas Superiores
        m1, m2, m3 = st.columns(3)
        m1.metric("Precio (LONG)", f"${precio_act:,.4f}")
        m2.metric("Wallet", f"${st.session_state.wallet:,.2f}")
        m3.metric("Cosecha Total", f"${st.session_state.cosecha:,.2f}", delta=f"RSI: {rsi_entrada}")

        # Gráfico Principal (Línea Dorada)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#F0B90B', width=3)))
        # Línea de precio actual
        fig.add_hline(y=precio_act, line_dash="solid", line_color="green", line_width=1)
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

        # Tablas de Malla y Historial (Como en la foto 1000266162.jpg)
        t1, t2 = st.columns(2)
        with t1:
            st.markdown("### 📋 Malla")
            # Generar malla visual si está vacía
            if not st.session_state.malla:
                st.session_state.malla = [{"id": i+1, "precio": round(precio_act * (1 - (i*distancia)), 2), "monto": round(inversion_total/niveles, 2), "estado": "PENDIENTE"} for i in range(niveles)]
                st.session_state.malla[0]["estado"] = "EJECUTADA"
            st.table(pd.DataFrame(st.session_state.malla))

        with t2:
            st.markdown("### 📜 Historial")
            if not st.session_state.historial:
                st.session_state.historial = [{"Fecha": "00:19:15", "Tipo": "SHORT", "Ganancia": 0.0159}]
            st.table(pd.DataFrame(st.session_state.
        
