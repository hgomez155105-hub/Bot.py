import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- FUNCIÓN PARA EL SONIDO DE VENTA ---
def reproducir_caja():
    # Sonido de caja registradora (URL pública)
    audio_url = "https://www.myinstants.com/media/sounds/cash-register-purchase.mp3"
    st.markdown(f'<audio src="{audio_url}" autoplay style="display:none;"></audio>', unsafe_allow_html=True)

# --- LOGO Y ESTILO ---
LOGO_OJO = "https://i.ibb.co/LzfNfXz/1000266017.png" 

st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_OJO, width=150)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
            'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
            'historial_pnl': [], 'direccion': 'LONG'
        })

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## 👁️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image(LOGO_OJO, width=100)
        par = st.selectbox("🎯 Objetivo Binance:", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"])
        
        st.divider()
        st.subheader("🔑 Conexión")
        entorno = st.radio("Entorno:", ["🟢 MODO DEMO", "🟡 MODO REAL"])
        api_key = st.text_input("API Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")
        
        st.divider()
        st.subheader("⚙️ Scalping")
        lev = st.slider("Apalancamiento", 1, 50, 50)
        tp_global = st.slider("Take Profit (%)", 0.01, 1.0, 0.10) / 100 
        inversion = st.number_input("Inversión (USDT)", 10.0, 5000.0, 100.0)
        
        if st.button("🚨 CERRAR TODO (PÁNICO)", use_container_width=True):
            st.session_state.update({'posiciones': [], 'ordenes_malla': []})
            st.rerun()

    # --- ALGORITMO PREDADOR ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    if bot_on:
        try:
            # Obtener precio actualizado
            res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={par.replace('/','')}")
            precio_act = float(res.json()['price'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

            # 1. DISPARO DE MALLA (REINICIO AUTOMÁTICO)
            if not st.session_state.ordenes_malla:
                st.session_state.direccion = "LONG" # Scalping en compra
                distancia = 0.001 
                monto_n = inversion / 10
                for i in range(10):
                    p_nivel = precio_act * (1 - (i * distancia))
                    st.session_state.ordenes_malla.append({'id': i+1, 'precio': round(p_nivel, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'})

            # 2. EJECUCIÓN DE COMPRAS
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE' and precio_act <= o['precio']:
                    if st.session_state.saldo_demo >= o['monto']:
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # 3. CIERRE RÁPIDO Y SONIDO
            if st.session_state.posiciones:
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                ganancia = (t_inv * (precio_act / p_prom - 1)) * lev

                if precio_act >= p_prom * (1 + tp_global):
                    # COSECHAR
                    reproducir_caja() # ¡CLINK!
                    st.session_state.historial_pnl.append({'Fecha': datetime.now().strftime("%H:%M:%S"), 'Ganancia': round(ganancia, 2)})
                    st.session_state.saldo_demo += (t_inv + ganancia)
                    st.session_state.ganancia_total += ganancia
                    
                    # REINICIO INMEDIATO (Para que no se detenga)
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.toast("💰 ¡PRESA CAPTURADA!"); time.sleep(0.5); st.rerun()

            # --- PANEL DE CONTROL ---
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Precio Real", f"${precio_act:,.2f}")
            col_m2.metric("Wallet Demo", f"${st.session_state.saldo_demo:,.2f}")
            col_m3.metric("Cosecha Total", f"${st.session_state.ganancia_total:,.2f}")

            # Gráfico de acción
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3), fill='tozeroy'))
            fig.update_layout(height=300, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # Tablas de seguimiento
            st.subheader("📋 Malla de Caza Activa")
            st.dataframe(st.session_state.ordenes_malla, use_container_width=True, height=200)

            time.sleep(1); st.rerun()
        except Exception as e:
            time.sleep(2); st.rerun()
