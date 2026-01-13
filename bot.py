import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONEXIÓN GOOGLE SHEETS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

def verificar_acceso(usuario, clave):
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.lower()
        match = df[(df['usuario'].astype(str).str.strip() == str(usuario).strip()) & 
                   (df['clave'].astype(str).str.strip() == str(clave).strip())]
        return not match.empty
    except: return False

st.set_page_config(page_title="H y G Inovaciones", layout="wide")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; color: white; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# --- PANTALLA DE ACCESO (REPARADA) ---
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=150)
        u_ingreso = st.text_input("Usuario")
        p_ingreso = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if verificar_acceso(u_ingreso, p_ingreso):
                st.session_state.autenticado = True
                st.session_state.user_name = u_ingreso
                st.rerun()
            else: st.error("Acceso denegado")
else:
    # --- MOTOR PREDADOR ---
    if 'precios_hist' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
            'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
            'historial_pnl': [], 'direccion': 'LONG', 'max_pnl_alcanzado': 0.0
        })

    with st.sidebar:
        st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=100)
        monedas = ["BTC/USDT", "SOL/USDT", "ETH/USDT", "BNB/USDT", "PEPE/USDT", "FET/USDT"]
        par = st.selectbox("🎯 Objetivo Binance:", monedas)
        bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR", value=True)
        
        st.divider()
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")
        
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 22)
        niveles = st.number_input("Niveles", 1, 50, 10)
        distancia = st.slider("Distancia (%)", 0.01, 1.0, 0.05) / 100
        inversion = st.number_input("Inversión USDT", 10.0, 10000.0, 100.0)

    # ACTUALIZACIÓN DE PRECIO EN TIEMPO REAL
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={par.replace('/', '')}"
        precio_act = float(requests.get(url).json()['price'])
        st.session_state.precios_hist.append(precio_act)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # UI PRINCIPAL
        st.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Precio {par}", f"${precio_act:,.4f}")
        c2.metric("Wallet Balance", f"${st.session_state.saldo_demo:,.2f}")
        c3.metric("PNL Total", f"${st.session_state.ganancia_total:,.2f}")

        # GRÁFICO AGRESIVO
        fig = go.Figure(go.Scatter(y=st.session_state.precios_hist, line=dict(color='#F0B90B', width=3)))
        fig.update_layout(height=350, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Malla de Operación")
        # Generación automática de malla si está vacía
        if not st.session_state.ordenes_malla:
            st.session_state.ordenes_malla = [{'id': i+1, 'precio': round(precio_act*(1-(i*distancia)),4), 'monto': inversion/niveles, 'estado': 'PENDIENTE'} for i in range(niveles)]
        st.dataframe(st.session_state.ordenes_malla, use_container_width=True)

        if bot_on:
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error("Conectando con Binance...")
        time.sleep(2)
        st.rerun()
                
