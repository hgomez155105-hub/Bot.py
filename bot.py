import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="wide")

LINK_DB = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"
LINK_TELEGRAM = "https://t.me/HyGinovaciones"

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
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LÓGICA DE LOGIN ---
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
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
    u = st.text_input("Usuario")
    c = st.text_input("Contraseña", type="password")
    if st.button("ACCEDER AL SISTEMA", use_container_width=True):
        if validar_usuario(u, c):
            st.session_state.autenticado, st.session_state.user_name = True, u
            st.rerun()
        else: st.error("❌ Licencia inválida.")
    st.markdown("</div>", unsafe_allow_html=True)
else:
    # --- INICIALIZACIÓN ---
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 'posiciones': [], 'precios_hist': [], 'ultimo_par': ""})

    with st.sidebar:
        st.header("🔐 Tus Credenciales")
        st.info("Tus llaves API no se guardan en el servidor, solo en tu sesión actual.")
        
        # EL USUARIO LAS PONE AQUÍ MANUALMENTE PARA PODER COMERCIALIZAR EL SOFT
        api_key_user = st.text_input("Binance API Key", type="password")
        api_secret_user = st.text_input("Binance Secret Key", type="password")
        
        st.markdown("---")
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        es_real = modo == "⚡ MODO REAL"
        
        # --- +20 MONEDAS (ARREGLADO) ---
        lista_monedas = [
            "SOL/USDT", "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", 
            "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "TRX/USDT", "LINK/USDT", "AVAX/USDT", 
            "SHIB/USDT", "FET/USDT", "RNDR/USDT", "PEPE/USDT", "WIF/USDT", "BONK/USDT",
            "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT", "NEAR/USDT", "LTC/USDT"
        ]
        par = st.selectbox("Seleccionar Activo:", lista_monedas)
        
        if par != st.session_state.ultimo_par:
            st.session_state.posiciones = []
            st.session_state.precios_hist = []
            st.session_state.ultimo_par = par

        leverage = st.slider("Apalancamiento", 1, 50, 20)
        monto = st.number_input("Monto (USDT)", value=10.0)
        tp_percent = st.slider("TP %", 0.1, 5.0, 0.5) / 100
        sl_percent = st.slider("SL %", 0.1, 5.0, 0.5) / 100

    st.subheader(f"Trading con {par}")
    bot_on = st.toggle("ENCENDER BOT")

    if bot_on:
        if es_real and (not api_key_user or not api_secret_user):
            st.error("⚠️ Error: Debes ingresar tus API Keys para operar en Real.")
            st.stop()
            
        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio = float(res['USD'])
            st.session_state.precios_hist.append(precio)
            if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)

            if not st.session_state.posiciones:
                st.session_state.posiciones.append({'entrada': precio, 'tp': precio * (1 + tp_percent), 'sl': precio * (1 - sl_percent)})
                if not es_real: st.session_state.saldo_demo -= monto

            for i, pos in enumerate(st.session_state.posiciones):
                if precio >= pos['tp'] or precio <= pos['sl']:
                    pnl = ((precio - pos['entrada']) / pos['entrada']) * leverage * monto
                    st.session_state.ganancia_acumulada += pnl
                    if not es_real: st.session_state.saldo_demo += (monto + pnl)
                    st.session_state.posiciones.pop(i)
                    st.rerun()

            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"<div class='metric-card'><div class='metric-label'>{par}</div><div class='metric-value'>${precio:,.4f}</div></div>", unsafe_allow_html=True)
            with col2: 
                bal = "⚡ REAL" if es_real else f"${st.session_state.saldo_demo:,.2f}"
                st.markdown(f"<div class='metric-card'><div class='metric-label'>BALANCE</div><div class='metric-value'>{bal}</div></div>", unsafe_allow_html=True)
            with col3: st.markdown(f"<div class='metric-card'><div class='metric-label'>GANANCIA</div><div class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

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
        except: time.sleep(1); st.rerun()
        
