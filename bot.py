import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")

LINK_DB = "https://docs.google.com/spreadsheets/d/1nYyINRPF-cIiAMsKInTxaO6wdptsitVfZnFq-o1Wo1Y/export?format=csv"

# --- CÁLCULO RSI ---
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

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 15px; text-align: center;
    }
    .metric-value { font-size: 1.4rem; font-weight: bold; color: #F0B90B; }
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
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            try:
                df = pd.read_csv(LINK_DB)
                df.columns = df.columns.str.strip().str.lower()
                check = df[(df['usuario'].astype(str) == str(user)) & (df['clave'].astype(str) == str(password))]
                if not check.empty:
                    st.session_state.autenticado = True
                    st.session_state.user_name = user
                    st.rerun()
                else: st.error("Datos incorrectos")
            except: st.error("Error conectando a la base de datos")
        st.markdown("</div>", unsafe_allow_html=True)
else:
    # --- INICIALIZACIÓN ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': ""
        })

    # --- SIDEBAR (CONFIGURACIÓN) ---
    with st.sidebar:
        st.title(f"👤 {st.session_state.user_name}")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
            
        st.divider()
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        
        st.subheader("⚙️ Estrategia")
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT"])
        
        # --- RESET AL CAMBIAR DE MONEDA ---
        if par != st.session_state.ultimo_par:
            st.session_state.precios_hist = []
            st.session_state.posiciones = []
            st.session_state.ordenes_malla = []
            st.session_state.ultimo_par = par
            st.rerun()

        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 15, 5)
        distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0.5) / 100
        inversion_total = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
        tp_global = st.slider("Take Profit Global (%)", 0.1, 10.0, 1.0) / 100
        rsi_seguridad = st.slider("Nivel RSI (Resguardo)", 20, 40, 30)

    # --- LOGICA DEL BOT ---
    st.subheader(f"Panel de Control: {par}")
    ejecutar = st.toggle("ACTIVAR ALGORITMO")

    if ejecutar:
        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_actual = float(res['USD'])
            st.session_state.precios_hist.append(precio_actual)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # 1. Crear Malla si no existe y RSI es bajo (Sobrevendido)
            if not st.session_state.posiciones and not st.session_state.ordenes_malla:
                if rsi_val <= rsi_seguridad:
                    monto_por_nivel = inversion_total / niveles
                    for i in range(niveles):
                        precio_nivel = precio_actual * (1 - (i * distancia))
                        st.session_state.ordenes_malla.append({
                            'precio': precio_nivel, 'monto': monto_por_nivel, 'estado': 'pendiente'
                        })
                    st.toast("Malla creada por señal RSI")

            # 2. Ejecutar niveles y DESCONTAR SALDO
            for orden in st.session_state.ordenes_malla:
                if orden['estado'] == 'pendiente' and precio_actual <= orden['precio']:
                    if st.session_state.saldo_demo >= orden['monto']:
                        orden['estado'] = 'ejecutada'
                        st.session_state.posiciones.append({'entrada': precio_actual, 'monto': orden['monto']})
                        st.session_state.saldo_demo -= orden['monto'] # DESCUENTO REAL
                    else:
                        st.warning("Fondos insuficientes para completar malla")

            # 3. Calcular Profit y Salida
            if st.session_state.posiciones:
                precio_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                target_profit = precio_promedio * (1 + tp_global)
                
                if precio_actual >= target_profit:
                    total_monto = sum(p['monto'] for p in st.session_state.posiciones)
                    pnl = (total_monto * tp_global) * lev
                    st.session_state.saldo_demo += (total_monto + pnl) # Devolvemos capital + ganancia
                    st.session_state.ganancia_acumulada += pnl
                    st.session_state.posiciones = []
                    st.session_state.ordenes_malla = []
                    st.balloons()
                    st.rerun()

            # --- DASHBOARD ---
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'>Precio {coin}<br><span class='metric-value'>${precio_actual:,.2f}</span></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'>Saldo Disponible<br><span class='metric-value'>${st.session_state.saldo_demo:,.2f}</span></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'>PNL Acumulado<br><span class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</span></div>", unsafe_allow_html=True)

            # --- GRÁFICO CON LÍNEAS DE NIVELES ---
            fig = go.Figure()
            # Línea de precio
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=2)))
            
            # Dibujar niveles de la malla
            for orden in st.session_state.ordenes_malla:
                color = "green" if orden['estado'] == 'ejecutada' else "gray"
                fig.add_hline(y=orden['precio'], line_dash="dash", line_color=color, annotation_text="COMPRA")
            
            # Dibujar Take Profit si hay posición
            if st.session_state.posiciones:
                precio_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                fig.add_hline(y=precio_promedio * (1 + tp_global), line_color="cyan", annotation_text="TAKE PROFIT")

            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"RSI Actual: {rsi_val:.2f} | Esperando RSI < {rsi_seguridad} para nueva malla")

            time.sleep(2); st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            time.sleep(2); st.rerun()
