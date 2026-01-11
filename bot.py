import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="centered")

# --- ESTILO MÓVIL Y LOGIN ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 10px; text-align: center;
    }
    .metric-label { font-size: 0.7rem; color: #848E9C; font-weight: bold; }
    .metric-value { font-size: 1.1rem; font-weight: bold; color: #F0B90B; }
    .login-box {
        background: #1E2329; padding: 25px; border-radius: 15px;
        border: 1px solid #F0B90B; margin-top: 50px;
    }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE AUTENTICACIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def login():
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #848E9C;'>Acceso Exclusivo</p>", unsafe_allow_html=True)
    
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Iniciar Sesión"):
            # AQUÍ PUEDES CAMBIAR TU USUARIO Y CLAVE
            if usuario == "admin" and clave == "1234":
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Datos incorrectos")
    with col2:
        if st.button("Registrarse"):
            st.info("Contacte a H y G Inovaciones para obtener una licencia.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- FLUJO PRINCIPAL ---
if not st.session_state.autenticado:
    login()
else:
    # --- INICIALIZACIÓN DE VARIABLES DEL BOT ---
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0,
            'saldo_real': 0.0,
            'ganancia_acumulada': 0.0,
            'posiciones': [],
            'precios_hist': [],
            'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"]),
            'ultimo_par': "",
            'ultimo_modo': ""
        })

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown("### 🚀 PANEL DE CONTROL")
        st.write(f"Conectado como: **Admin**")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        
        st.markdown("---")
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL (BINANCE)"])
        es_real = modo == "⚡ MODO REAL (BINANCE)"
        
        if es_real:
            with st.expander("🔑 API BINANCE", expanded=True):
                api_key = st.text_input("API Key", type="password")
                api_secret = st.text_input("Secret Key", type="password")
        
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
        
        # AUTO-RESET
        if par != st.session_state.ultimo_par or modo != st.session_state.ultimo_modo:
            st.session_state.posiciones = []
            st.session_state.precios_hist = []
            st.session_state.ultimo_par = par
            st.session_state.ultimo_modo = modo
            
        leverage = st.slider("Apalancamiento", 1, 50, 25)
        monto = st.number_input("Inversión (USDT)", value=2.0)
        dist_grid = st.slider("Profit (%)", 0.05, 1.0, 0.1) / 100

    # --- INTERFAZ DEL BOT ---
    st.markdown("<p style='text-align: center; color: #848E9C;'>Reciba un cordial saludo de <b>H y G inovaciones</b></p>", unsafe_allow_html=True)
    bot_on = st.toggle("EJECUTAR ALGORITMO")

    if bot_on:
        try:
            # Obtención de Precio
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio = float(res['USD'])
            st.session_state.precios_hist.append(precio)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

            # LÓGICA DE COMPRA
            if not st.session_state.posiciones:
                st.session_state.posiciones.append({'precio': precio, 'id': 1})
                if not es_real: st.session_state.saldo_demo -= monto

            # LÓGICA DE CIERRE
            for i, pos in enumerate(st.session_state.posiciones):
                target = pos['precio'] * (1 + dist_grid)
                if precio >= target:
                    pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto
                    if not es_real: st.session_state.saldo_demo += (monto + pnl)
                    st.session_state.ganancia_acumulada += pnl
                    
                    new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": f"WIN {par}", "Precio": precio, "PNL": f"${pnl:.2f}"}])
                    st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                    st.session_state.posiciones.pop(i)
                    st.rerun()

            # --- PANEL MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>PRECIO</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
            with c2: 
                v_bal = st.session_state.saldo_real if es_real else st.session_state.saldo_demo
                st.markdown(f"<div class='metric-card'><div class='metric-label'>WALLET</div><div class='metric-value' style='color:#F0B90B;'>${v_bal:,.2f}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>GANADO</div><div class='metric-value' style='color:#00FFAA;'>${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

            # --- GRÁFICO ---
            fig = go.Figure(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00', width=2)))
            for p in st.session_state.posiciones:
                fig.add_hline(y=p['precio'], line_color="white", annotation_text="ENTRY")
                fig.add_hline(y=p['precio']*(1+dist_grid), line_color="#F0B90B", line_dash="dash")
            
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            st.dataframe(st.session_state.log_df.head(5), use_container_width=True)
            time.sleep(2)
            st.rerun()

        except Exception:
            time.sleep(1)
            st.rerun()
                    
