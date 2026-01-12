import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="☀️")

# --- FUNCIÓN BINANCE TOP 20 ---
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
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0); perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:]); avg_loss = np.mean(perdidas[-periodo:])
    return 100 - (100 / (1 + (avg_gain / (avg_loss if avg_loss != 0 else 0.001))))

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    .status-box { padding: 10px; border-radius: 10px; border: 1px solid #333; background: #1E2329; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

LOGO_SOL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Sol_de_Mayo-Bandera_de_Argentina.svg/1200px-Sol_de_Mayo-Bandera_de_Argentina.svg.png"

# --- LOGIN ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.image(LOGO_SOL, width=120)
        st.markdown("<h1 style='text-align: center;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL TERMINAL PREDADOR", use_container_width=True):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    # --- SESIÓN ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
            'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
            'historial_pnl': [], 'direccion': 'LONG', 'velas': []
        })

    # --- HEADER ---
    h1, h2 = st.columns([4, 1])
    h1.markdown(f"### ☀️ H y G Inovaciones - 👤 {st.session_state.user_name}")
    h2.image(LOGO_SOL, width=50)

    # --- SIDEBAR ---
    with st.sidebar:
        par = st.selectbox("🎯 Selección de Activo:", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par, 'velas': []}); st.rerun()
        
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 40, 10)
        distancia = st.slider("Distancia entre niveles (%)", 0.01, 2.0, 0.1) / 100
        inversion = st.number_input("Capital Total (USDT)", 10.0, 10000.0, 100.0)
        tp_global = st.slider("Take Profit (%)", 0.01, 5.0, 0.15) / 100

    # --- LÓGICA DE TRADING ---
    bot_on = st.toggle("🚀 INICIAR ALGORITMO PREDADOR")
    
    if bot_on:
        try:
            # Captura de datos
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            p_act = float(res['USD'])
            st.session_state.precios_hist.append(p_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            
            # Cálculo de tendencia simple (EMA 10)
            ema = np.mean(st.session_state.precios_hist[-10:]) if len(st.session_state.precios_hist) >= 10 else p_act
            tendencia = "LONG" if p_act >= ema else "SHORT"
            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # 1. ABRIR MALLA
            if not st.session_state.ordenes_malla:
                st.session_state.direccion = tendencia
                m_nivel = inversion / niveles
                for i in range(niveles):
                    f = (1 - (i * distancia)) if st.session_state.direccion == "LONG" else (1 + (i * distancia))
                    st.session_state.ordenes_malla.append({'id': i+1, 'precio': round(p_act * f, 4), 'monto': round(m_nivel, 2), 'estado': 'PENDIENTE'})
                st.toast(f"Modo {st.session_state.direccion} activado")

            # 2. EJECUCIÓN
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit = (st.session_state.direccion == "LONG" and p_act <= o['precio']) or \
                          (st.session_state.direccion == "SHORT" and p_act >= o['precio'])
                    if hit:
                        if st.session_state.saldo_demo >= o['monto']:
                            st.session_state.saldo_demo -= o['monto']
                            o['estado'] = 'EJECUTADA'
                            st.session_state.posiciones.append({'entrada': p_act, 'monto': o['monto']})

            # 3. CIERRE (PICOTEO)
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                t_inv = sum(p['monto'] for p in st.session_state.posiciones)
                
                if st.session_state.direccion == "LONG":
                    ganancia = (t_inv * (p_act / p_prom - 1)) * lev
                    cierra = p_act >= p_prom * (1 + tp_global)
                else:
                    ganancia = (t_inv * (1 - p_act / p_prom)) * lev
                    cierra = p_act <= p_prom * (1 - tp_global)

                if cierra and ganancia > 0:
                    st.session_state.historial_pnl.append({'Hora': datetime.now().strftime("%H:%M:%S"), 'Par': par, 'Tipo': st.session_state.direccion, 'PNL': round(ganancia, 2)})
                    st.session_state.saldo_demo += (t_inv + ganancia)
                    st.session_state.ganancia_total += ganancia
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- INTERFAZ ---
            c1, c2, c3 = st.columns(3)
            with c1: 
                icon = "🚀" if st.session_state.direccion == "LONG" else "🏹"
                st.metric(f"Precio {icon}", f"${p_act:,.4f}", f"Modo {st.session_state.direccion}")
            with c2: st.metric("Saldo Demo", f"${st.session_state.saldo_demo:,.2f}")
            with c3: st.metric("Cosecha Total", f"${st.session_state.ganancia_total:,.2f}", f"RSI: {rsi_val:.1f}")

            # Gráfico de Velas (Candlestick Simulado)
            fig = go.Figure(data=[go.Scatter(x=list(range(len(st.session_state.precios_hist))), y=st.session_state.precios_hist, line=dict(color='#F0B90B', width=2), fill='tozeroy')])
            for o in st.session_state.ordenes_malla:
                fig.add_hline(y=o['precio'], line_dash="dash", line_color="#00FF00" if o['estado'] == 'EJECUTADA' else "#555")
            fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)

            cola, colb = st.columns(2)
            cola.subheader("📋 Malla Activa"); cola.dataframe(st.session_state.ordenes_malla, use_container_width=True)
            colb.subheader("📜 Capturas Realizadas"); colb.dataframe(st.session_state.historial_pnl[::-1], use_container_width=True)

            time.sleep(1); st.rerun()
        except: time.sleep(1); st.rerun()

