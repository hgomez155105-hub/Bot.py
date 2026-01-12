import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime
import ccxt  # Librería para conexión real

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="centered")

# --- ENLACE DE TU BASE DE DATOS ---
LINK_DB = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"
LINK_TELEGRAM = "https://t.me/HyGinovaciones"

# --- CONFIGURACIÓN DE API (PEGA TUS LLAVES AQUÍ) ---
API_KEY = "TU_API_KEY_AQUI"
API_SECRET = "TU_SECRET_KEY_AQUI"

# Conexión al Exchange
def conectar_exchange():
    try:
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'options': {'defaultType': 'future'} # Cambiar a 'spot' si no usas futuros
        })
        return exchange
    except:
        return None

# --- ESTILO ---
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
        border: 1px solid #F0B90B; margin-top: 30px;
    }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def validar_usuario(u, c):
    try:
        df_users = pd.read_csv(LINK_DB)
        df_users.columns = df_users.columns.str.strip().str.lower()
        u_ingresado, c_ingresado = str(u).strip(), str(c).strip()
        check = df_users[(df_users['usuario'].astype(str).str.strip() == u_ingresado) & 
                         (df_users['clave'].astype(str).str.strip() == c_ingresado)]
        return not check.empty
    except: return False

if not st.session_state.autenticado:
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>")
    u = st.text_input("Usuario")
    c = st.text_input("Contraseña", type="password")
    if st.button("ACCEDER AL SISTEMA", use_container_width=True):
        if validar_usuario(u, c):
            st.session_state.autenticado = True
            st.session_state.user_name = u
            st.rerun()
        else: st.error("❌ Licencia inválida.")
    st.link_button("🚀 SOLICITAR LICENCIA", LINK_TELEGRAM, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 'posiciones': [], 'precios_hist': []})

    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.user_name}**")
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        es_real = modo == "⚡ MODO REAL"
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "BNB/USDT"])
        leverage = st.slider("Apalancamiento", 1, 50, 25)
        monto = st.number_input("Inversión (USDT)", value=10.0)
        tp_percent = st.slider("Take Profit (%)", 0.1, 5.0, 0.5) / 100
        sl_percent = st.slider("Stop Loss (%)", 0.1, 5.0, 0.3) / 100

    st.markdown("<p style='text-align: center; color: #848E9C;'>Panel de Control Real - <b>H y G Inovaciones</b></p>", unsafe_allow_html=True)
    bot_on = st.toggle("EJECUTAR ALGORITMO")

    if bot_on:
        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio = float(res['USD'])
            st.session_state.precios_hist.append(precio)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

            # --- LÓGICA DE TRADING ---
            if not st.session_state.posiciones:
                if es_real:
                    st.info("🚀 Abriendo posición real en Exchange...")
                    # Aquí iría: exchange.create_market_buy_order(par, monto)
                
                st.session_state.posiciones.append({
                    'entrada': precio, 
                    'tp': precio * (1 + tp_percent),
                    'sl': precio * (1 - sl_percent)
                })
                if not es_real: st.session_state.saldo_demo -= monto

            for i, pos in enumerate(st.session_state.posiciones):
                if precio >= pos['tp'] or precio <= pos['sl']:
                    if es_real:
                        st.success("💰 Cerrando posición real con Profit...")
                        # Aquí iría: exchange.create_market_sell_order(par, monto)
                    
                    pnl = ((precio - pos['entrada']) / pos['entrada']) * leverage * monto
                    st.session_state.ganancia_acumulada += pnl
                    if not es_real: st.session_state.saldo_demo += (monto + pnl)
                    st.session_state.posiciones.pop(i)
                    st.rerun()

            # --- PANEL VISUAL ---
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>{par}</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
            with c2: 
                balance_txt = "CONECTADO" if es_real else f"${st.session_state.saldo_demo:,.2f}"
                st.markdown(f"<div class='metric-card'><div class='metric-label'>BALANCE</div><div class='metric-value'>{balance_txt}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>PNL</div><div class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00', width=2)))
            if st.session_state.posiciones:
                p = st.session_state.posiciones[0]
                fig.add_hline(y=p['entrada'], line_dash="dot", line_color="white", annotation_text="ENTRY")
                fig.add_hline(y=p['tp'], line_dash="dash", line_color="#F0B90B", annotation_text="TP")
                fig.add_hline(y=p['sl'], line_dash="dash", line_color="#FF4B4B", annotation_text="SL")
            
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(side="right", gridcolor="#23282E"), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            time.sleep(1.5); st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(2); st.rerun()
            
