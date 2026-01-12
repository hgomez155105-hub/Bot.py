import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")

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
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #F0B90B; }
    .login-box {
        background: #1E2329; padding: 30px; border-radius: 15px;
        border: 1px solid #F0B90B; margin: auto; max-width: 400px;
    }
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            try:
                df = pd.read_csv(LINK_DB)
                df.columns = df.columns.str.strip().str.lower()
                check = df[(df['usuario'].astype(str) == str(user)) & (df['clave'].astype(str) == str(password))]
                if not check.empty:
                    st.session_state.autenticado = True
                    st.session_state.user_name = user
                    st.rerun()
                else: st.error("Datos incorrectos")
            except: st.error("Error de conexión con DB")
        st.markdown("</div>", unsafe_allow_html=True)
else:
    # --- INICIALIZACIÓN DE ESTADOS ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_pendientes': [], 'ultimo_par': ""
        })

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.title(f"👤 {st.session_state.user_name}")
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        
        st.subheader("📊 Configuración")
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT", "PEPE/USDT"])
        
        # --- RESET AL CAMBIAR MONEDA ---
        if par != st.session_state.ultimo_par:
            st.session_state.precios_hist = []
            st.session_state.posiciones = []
            st.session_state.ordenes_pendientes = []
            st.session_state.ultimo_par = par
            st.rerun()

        lev = st.slider("Apalancamiento", 1, 50, 20)
        niv = st.number_input("Niveles de Malla", 1, 10, 5)
        dist = st.slider("Distancia (%)", 0.1, 5.0, 0.5) / 100
        monto_total = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
        tp_manual = st.slider("Take Profit (%)", 0.1, 5.0, 0.5) / 100
        
        st.subheader("🔑 API Keys (Solo Real)")
        api_k = st.text_input("API Key", type="password")
        api_s = st.text_input("Secret Key", type="password")

    # --- PANEL PRINCIPAL ---
    st.subheader(f"Trading: {par}")
    bot_on = st.toggle("EJECUTAR ALGORITMO")

    if bot_on:
        try:
            # Obtener precio
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_actual = float(res['USD'])
            st.session_state.precios_hist.append(precio_actual)
            if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)

            # Crear Malla Inicial
            if not st.session_state.posiciones and not st.session_state.ordenes_pendientes:
                m_por_nivel = monto_total / niv
                for n in range(niv):
                    st.session_state.ordenes_pendientes.append({
                        'precio': precio_actual * (1 - (n * dist)),
                        'monto': m_por_nivel, 'ejecutada': False
                    })

            # Ejecutar Compras y DESCONTAR SALDO
            for o in st.session_state.ordenes_pendientes:
                if not o['ejecutada'] and precio_actual <= o['precio']:
                    if st.session_state.saldo_demo >= o['monto']:
                        o['ejecutada'] = True
                        st.session_state.posiciones.append({'entrada': precio_actual, 'monto': o['monto']})
                        # AQUÍ SE DESCUENTA EL DINERO DEL SALDO DEMO
                        st.session_state.saldo_demo -= o['monto']
                        st.toast(f"Compra ejecutada a ${precio_actual}")
                    else:
                        st.error("Saldo insuficiente en Demo")

            # Cierre de Operación
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                if precio_actual >= p_prom * (1 + tp_manual):
                    tot_invertido = sum(p['monto'] for p in st.session_state.posiciones)
                    pnl_bruto = ((precio_actual - p_prom) / p_prom) * lev * tot_invertido
                    
                    # Devolver capital + ganancia al saldo
                    st.session_state.saldo_demo += (tot_invertido + pnl_bruto)
                    st.session_state.ganancia_acumulada += pnl_bruto
                    st.session_state.update({'posiciones': [], 'ordenes_pendientes': []})
                    st.balloons()
                    st.rerun()

            # Dashboard
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>Precio {coin}</div><div class='metric-value'>${precio_actual:,.2f}</div></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>Disponible (DEMO)</div><div class='metric-value'>${st.session_state.saldo_demo:,.2f}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>Ganancia Total</div><div class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

            # Gráfico scannable
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name="Precio", line=dict(color='#F0B90B')))
            st.plotly_chart(fig, use_container_width=True)
            
            time.sleep(2); st.rerun()
        except Exception as e:
            time.sleep(2); st.rerun()
        
