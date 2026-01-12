import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="☀️")

# --- FUNCIONES DE APOYO ---
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
    .panic-btn { background-color: #FF4B4B !important; color: white !important; font-weight: bold !important; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

LOGO_SOL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Sol_de_Mayo-Bandera_de_Argentina.svg/1200px-Sol_de_Mayo-Bandera_de_Argentina.svg.png"

# --- LOGIN ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.image(LOGO_SOL, width=120)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL TERMINAL PREDADOR", use_container_width=True):
            st.session_state.autenticado = True; st.session_state.user_name = u; st.rerun()
else:
    # --- INICIALIZACIÓN DE SESIÓN ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 'posiciones': [], 
            'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': "", 
            'historial_pnl': [], 'direccion': 'LONG'
        })

    # --- HEADER ---
    h1, h2 = st.columns([4, 1])
    h1.markdown(f"### ☀️ H y G Inovaciones - 👤 {st.session_state.user_name}")
    h2.image(LOGO_SOL, width=50)

    # --- SIDEBAR (CONTROLES) ---
    with st.sidebar:
        par = st.selectbox("🎯 Objetivo (Top 20 Binance):", obtener_top_20_binance())
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par}); st.rerun()
        
        st.divider()
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Niveles de Malla", 1, 40, 10)
        distancia = st.slider("Distancia entre niveles (%)", 0.01, 1.0, 0.05) / 100
        inversion = st.number_input("Inversión por Malla (USDT)", 10.0, 10000.0, 100.0)
        tp_global = st.slider("Take Profit (%)", 0.01, 2.0, 0.10) / 100

        st.divider()
        # BOTÓN DE PÁNICO
        if st.button("🚨 BOTÓN DE PÁNICO: CERRAR TODO", use_container_width=True):
            if st.session_state.posiciones:
                st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                st.warning("Todas las operaciones han sido cerradas forzosamente.")
                st.rerun()

    # --- LÓGICA DEL BOT ---
    bot_on = st.toggle("🚀 ACTIVAR ALGORITMO PREDADOR")
    
    if bot_on:
        try:
            # Obtención de precio y RSI
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={par.split('/')[0]}&tsyms=USD").json()
            p_act = float(res['USD'])
            st.session_state.precios_hist.append(p_act)
            if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)
            
            # Detección de tendencia (EMA 10)
            ema = np.mean(st.session_state.precios_hist[-10:]) if len(st.session_state.precios_hist) >= 10 else p_act
            tendencia_actual = "LONG" if p_act >= ema else "SHORT"
            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # 1. DISPARO DE MALLA DINÁMICO
            if not st.session_state.ordenes_malla:
                st.session_state.direccion = tendencia_actual
                monto_n = inversion / niveles
                for i in range(niveles):
                    # Factor de malla: si es LONG compra hacia abajo, si es SHORT vende hacia arriba
                    f = (1 - (i * distancia)) if st.session_state.direccion == "LONG" else (1 + (i * distancia))
                    st.session_state.ordenes_malla.append({
                        'id': i+1, 'precio': round(p_act * f, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'
                    })
                st.toast(f"Estrategia {st.session_state.direccion} iniciada.")

            # 2. EJECUCIÓN DE ÓRDENES
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE':
                    hit = (st.session_state.direccion == "LONG" and p_act <= o['precio']) or \
                          (st.session_state.direccion == "SHORT" and p_act >= o['precio'])
                    if hit:
                        if st.session_state.saldo_demo >= o['monto']:
                            st.session_state.saldo_demo -= o['monto']
                            o['estado'] = 'EJECUTADA'
                            st.session_state.posiciones.append({'entrada': p_act, 'monto': o['monto']})

            # 3. CIERRE POR PROFIT (PICOTEO)
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
                    st.session_state.historial_pnl.append({
                        'Hora': datetime.now().strftime("%H:%M:%S"), 
                        'Par': par, 
                        'Modo': st.session_state.direccion, 
                        'Captura': f"+${ganancia:.2f}"
                    })
                    st.session_state.saldo_demo += (t_inv + ganancia)
                    st.session_state.ganancia_total += ganancia
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons()
                    st.rerun()

            # --- PANEL DE CONTROL VISUAL ---
            c1, c2, c3 = st.columns(3)
            with c1: 
                icon = "🚀" if st.session_state.direccion == "LONG" else "🏹"
                st.metric(f"Precio ({icon} {st.session_state.direccion})", f"${p_act:,.4f}")
            with c2: st.metric("Saldo Billetera", f"${st.session_state.saldo_demo:,.2f}")
            with c3: st.metric("Cosecha Acumulada", f"${st.session_state.ganancia_total:,.2f}", f"RSI: {rsi_val:.1f}")

            # Gráfico de Área Predador
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, fill='tozeroy', line=dict(color='#F0B90B', width=2), name="Precio"))
            for o in st.session_state.ordenes_malla:
                line_color = "rgba(0, 255, 0, 0.6)" if o['estado'] == 'EJECUTADA' else "rgba(255, 255, 255, 0.2)"
                fig.add_hline(y=o['precio'], line_dash="dash", line_color=line_color)
            
            fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=10))
            st.plotly_chart(fig, use_container_width=True)

            # Tablas de Datos
            col_izq, col_der = st.columns(2)
            with col_izq: 
                st.markdown("##### 📋 Malla de Captura")
                st.dataframe(st.session_state.ordenes_malla, use_container_width=True, height=250)
            with col_der: 
                st.markdown("##### 📜 Historial de Capturas")
                st.dataframe(st.session_state.historial_pnl[::-1], use_container_width=True, height=250)

            time.sleep(1)
            st.rerun()

        except Exception as e:
            time.sleep(1)
            st.rerun()
    
