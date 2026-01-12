import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="📈")

# --- FUNCIÓN PARA OBTENER TENDENCIAS DE BINANCE ---
def obtener_top_20_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        # Filtrar solo pares contra USDT y ordenar por volumen
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        # Formatear para el selectbox (ej: BTC/USDT)
        simbolos = [f"{s[:-4]}/USDT" for s in top_20['symbol']]
        return simbolos
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT", "BNB/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

# --- ESTILOS Y LOGO ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .main-header { font-size: 2.5rem; color: #F0B90B; text-align: center; font-weight: bold; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    </style>
    """, unsafe_allow_html=True)

# URL del logo (puedes cambiarla por tu link directo)
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/1991/1991047.png" 

# --- SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image(LOGO_URL, width=100)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        user_input = st.text_input("Usuario")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            if user_input and pass_input: # Aquí va tu lógica de DB
                st.session_state.autenticado = True
                st.session_state.user_name = user_input
                st.rerun()
else:
    # --- INICIALIZACIÓN DE ESTADOS ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 
            'ultimo_par': "", 'historial_cierres': []
        })

    # --- ENCABEZADO PRINCIPAL ---
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown(f"## 🚀 H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    with head_col2:
        st.image(LOGO_URL, width=50)

    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader("🌐 Mercado en Tendencia")
        monedas_trend = obtener_top_20_binance()
        par = st.selectbox("Seleccionar Activo (Top 20 Binance):", monedas_trend)
        
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
            st.rerun()

        st.divider()
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        st.text_input("API Key", type="password")
        st.text_input("Secret Key", type="password")
        
        st.subheader("⚙️ Estrategia")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 15, 5)
        distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0.5) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
        rsi_venta = st.slider("RSI Cierre", 50, 90, 65)
        tp_global = st.slider("Take Profit (%)", 0.1, 10.0, 1.0) / 100

    # --- LÓGICA BOT ---
    bot_on = st.toggle("ENCENDER ALGORITMO")

    if bot_on:
        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # Malla e Inversión
            if not st.session_state.ordenes_malla:
                monto_nivel = inversion / niveles
                for i in range(niveles):
                    p_n = precio_act * (1 - (i * distancia))
                    st.session_state.ordenes_malla.append({
                        'id': i+1, 'precio': round(p_n, 4), 'monto': round(monto_nivel, 2), 'estado': 'PENDIENTE'
                    })

            # Ejecutar y Descontar
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE' and precio_act <= o['precio']:
                    if st.session_state.saldo_demo >= o['monto']:
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # Cierre y Registro
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                p_tp = p_prom * (1 + tp_global)
                if precio_act >= p_tp and rsi_val >= rsi_venta:
                    total_rec = sum(p['monto'] for p in st.session_state.posiciones)
                    pnl = (total_rec * tp_global) * lev
                    st.session_state.historial_cierres.append({
                        'Hora': datetime.now().strftime("%H:%M:%S"),
                        'Activo': par, 'Ganancia': round(pnl, 2)
                    })
                    st.session_state.saldo_demo += (total_rec + pnl)
                    st.session_state.ganancia_acumulada += pnl
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # Dashboard
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio {coin}", f"${precio_act:,.4f}")
            c2.metric("Balance Disponible", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("PNL General", f"${st.session_state.ganancia_acumulada:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # Gráfico
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B')))
            for o in st.session_state.ordenes_malla:
                color = "green" if o['estado'] == 'EJECUTADA' else "rgba(100,100,100,0.4)"
                fig.add_hline(y=o['precio'], line_dash="dash", line_color=color)
            st.plotly_chart(fig, use_container_width=True)

            # TABLAS
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📋 Malla Activa")
                st.dataframe(st.session_state.ordenes_malla, use_container_width=True)
            with col_b:
                st.subheader("📜 Historial PNL por Moneda")
                st.dataframe(st.session_state.historial_cierres, use_container_width=True)

            time.sleep(1); st.rerun()
        except Exception:
            time.sleep(1); st.rerun()
                
