import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="wide")

LINK_DB = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

# --- LÓGICA RSI ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 15px; text-align: center;
    }
    .metric-label { font-size: 0.8rem; color: #848E9C; }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #F0B90B; }
    .login-box {
        background: #1E2329; padding: 30px; border-radius: 15px;
        border: 1px solid #F0B90B; margin: auto; max-width: 400px;
    }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- FUNCIÓN VALIDAR USUARIO ---
def validar_usuario(u, c):
    try:
        df_users = pd.read_csv(LINK_DB)
        df_users.columns = df_users.columns.str.strip().str.lower()
        u_ingresado, c_ingresado = str(u).strip(), str(c).strip()
        check = df_users[(df_users['usuario'].astype(str).str.strip() == u_ingresado) & 
                         (df_users['clave'].astype(str).str.strip() == c_ingresado)]
        return not check.empty
    except: return False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if validar_usuario(user, password):
                st.session_state.autenticado = True
                st.session_state.user_name = user
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas.")
        st.markdown("</div>", unsafe_allow_html=True)
else:
    # --- INICIALIZACIÓN DE TRADING ---
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_pendientes': [], 'ultimo_par': ""
        })

    # --- BARRA LATERAL: CONTROLES MANUALES ---
    with st.sidebar:
        st.title(f"👤 {st.session_state.user_name}")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
            
        st.markdown("---")
        modo = st.radio("ENTORNO:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        es_real = modo == "⚡ MODO REAL"
        
        st.subheader("🔑 APIs Manuales")
        api_k = st.text_input("Binance API Key", type="password")
        api_s = st.text_input("Binance Secret Key", type="password")
        
        st.subheader("🛡️ Resguardo RSI")
        rsi_m = st.slider("Nivel RSI Manual", 50, 95, 70)
        
        st.subheader("📊 Estrategia")
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT", "PEPE/USDT", "RNDR/USDT"])
        
        if par != st.session_state.ultimo_par:
            st.session_state.update({'posiciones': [], 'ordenes_pendientes': [], 'ultimo_par': par})

        lev = st.slider("Apalancamiento Manual", 1, 50, 20)
        niv = st.number_input("Niveles de Malla", 1, 20, 5)
        dist = st.slider("Distancia entre órdenes (%)", 0.1, 5.0, 1.0) / 100
        monto = st.number_input("Inversión Total (USDT)", value=50.0)
        tp_m = st.slider("Profit Global Manual (%)", 0.1, 5.0, 0.5) / 100

    # --- PANEL PRINCIPAL ---
    st.subheader(f"Panel de Control: {par} ({modo})")
    bot_on = st.toggle("EJECUTAR ALGORITMO")

    if bot_on:
        if es_real and (not api_k or not api_s):
            st.warning("⚠️ Configura tus API Keys en la barra lateral.")
            st.stop()

        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_actual = float(res['USD'])
            st.session_state.precios_hist.append(precio_actual)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            
            rsi_actual = calcular_rsi(st.session_state.precios_hist)

            # Malla
            if not st.session_state.posiciones and not st.session_state.ordenes_pendientes:
                m_nivel = monto / niv
                for n in range(niv):
                    st.session_state.ordenes_pendientes.append({'precio': precio_actual * (1-(n*dist)), 'monto': m_nivel, 'ejecutada': False})

            # Compras
            for o in st.session_state.ordenes_pendientes:
                if not o['ejecutada'] and precio_actual <= o['precio']:
                    o['ejecutada'] = True
                    st.session_state.posiciones.append({'entrada': precio_actual, 'monto': o['monto']})

            # Cierre
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                en_verde = precio_actual > p_prom
                if (precio_actual >= p_prom * (1+tp_m)) or (rsi_actual >= rsi_m and en_verde):
                    total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                    pnl = ((precio_actual - p_prom) / p_prom) * lev * total_inv
                    st.session_state.ganancia_acumulada += pnl
                    if not es_real: st.session_state.saldo_demo += (total_inv + pnl)
                    st.session_state.update({'posiciones': [], 'ordenes_pendientes': []})
                    st.rerun()

            # Dashboard
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>{par}</div><div class='metric-value'>${precio_actual:,.4f}</div></div>", unsafe_allow_html=True)
            with c2: 
                bal = f"${st.session_state.saldo_demo:,.2f}" if not es_real else "⚡ REAL"
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Balance</div><div class='metric-value'>{bal}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>PNL</div><div class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

            # Gráfico
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00')))
            for o in st.session_state.ordenes_pendientes:
                fig.add_hline(y=o['precio'], line_dash="dot", line_color="white" if not o['ejecutada'] else "#0088FF")
            
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True)
            
            time.sleep(1.5); st.rerun()
        except: time.sleep(1); st.rerun()
        
