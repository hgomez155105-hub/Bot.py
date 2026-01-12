import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="☀️")

def obtener_top_20_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except: return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios); ganancias = deltas.clip(min=0); perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:]); avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / (avg_loss if avg_loss != 0 else 0.001))))

# --- ESTILO VISUAL (Basado en tus capturas) ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_SOL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Sol_de_Mayo-Bandera_de_Argentina.svg/1200px-Sol_de_Mayo-Bandera_de_Argentina.svg.png"

if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_SOL, width=120)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL MODO PREDADOR", use_container_width=True):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    # --- ESTADO INICIAL ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 'historial_pnl': [], 'direccion': 'LONG'})

    # --- HEADER ---
    c_h1, c_h2 = st.columns([4, 1])
    c_h1.markdown(f"## ☀️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    c_h2.image(LOGO_SOL, width=50)

    # --- SIDEBAR (Controles de la captura) ---
    with st.sidebar:
        par = st.selectbox("🎯 Objetivo (Top 20):", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par}); st.rerun()
        
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 50)
        niveles = st.number_input("Niveles de Malla", 1, 30, 10)
        distancia = st.slider("Distancia entre niveles (%)", 0.01, 1.0, 0.09) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 10.0)
        
        st.subheader("🛠️ Parámetros de Caza")
        rsi_entrada = st.slider("RSI Entrada", 10, 70, 52)
        tp_global = st.slider("Take Profit (%)", 0.01, 2.0, 0.15) / 100

        st.divider()
        if st.button("🚨 BOTÓN DE PÁNICO: CERRAR TODO", use_container_width=True):
            st.session_state.update({'posiciones': [], 'ordenes_malla': []})
            st.warning("Operaciones cerradas y malla limpia.")
            st.rerun()

    # --- LÓGICA DEL BOT ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    
    if bot_on:
        try:
            # Obtener precio
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            
            # Tendencia y RSI
            ema_rapida = np.mean(st.session_state.precios_hist[-10:]) if len(st.session_state.precios_hist) >= 10 else precio_act
            tendencia = "LONG" if precio_act >= ema_rapida else "SHORT"
            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # 1. CREAR MALLA SI NO EXISTE
            if not st.session_state.ordenes_malla:
                st.session_state.direccion = tendencia
                monto_n = inversion / niveles
                for i in range(niveles):
                    factor = (1 - (i * distancia)) if st.session_state.direccion == "LONG" else (1 + (i * distancia))
                    st.session_state.ordenes_malla.append({
                        'id': i+1, 'precio': round(precio_act * factor, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'
                    })
                st.toast(f"Malla {st.session_state.direccion} desplegada")

            # 2. EJECUTAR ÓRDENES
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    toco = (st.session_state.direccion == "LONG" and precio_act <= o['precio']) or \
                           (st.session_state.direccion == "SHORT" and precio_act >= o['precio'])
                    if toco:
                        if st.session_state.saldo_demo >= o['monto']:
                            st.session_state.saldo_demo -= o['monto']
                            o['estado'] = 'EJECUTADA'
                            st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})

            # 3. VERIFICAR CIERRE (PICOTEO)
            if st.session_state.posiciones:
                total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                p_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                
                if st.session_state.direccion == "LONG":
                    ganancia = (total_inv * (precio_act / p_promedio - 1)) * lev
                    toca_tp = precio_act >= p_promedio * (1 + tp_global)
                else:
                    ganancia = (total_inv * (1 - precio_act / p_promedio)) * lev
                    toca_tp = precio_act <= p_promedio * (1 - tp_global)

                if toca_tp and ganancia > 0:
                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M:%S"), 
                        'Par': par, 'Tipo': st.session_state.direccion, 'Ganancia': round(ganancia, 4)
                    })
                    st.session_state.saldo_demo += (total_inv + ganancia)
                    st.session_state.ganancia_total += ganancia
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- RENDERIZADO (IGUAL A TUS FOTOS) ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio ({st.session_state.direccion})", f"${precio_act:,.4f}")
            c2.metric("Saldo Disponible", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("Cosecha Total", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # Gráfico Línea Amarilla
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, line=dict(color='#F0B90B', width=2), name="Precio"))
            for o in st.session_state.ordenes_malla:
                color = "green" if o['estado'] == 'EJECUTADA' else "grey"
                fig.add_hline(y=o['precio'], line_dash="dash", line_color=color)
            fig.update_layout(height=350, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a: 
                st.markdown("##### 📋 Malla")
                st.dataframe(st.session_state.ordenes_malla, use_container_width=True, height=250)
            with col_b: 
                st.markdown("##### 📜 Historial")
                st.dataframe(st.session_state.historial_pnl[::-1], use_container_width=True, height=250)

            time.sleep(1); st.rerun()
        except: time.sleep(1); st.rerun()
