import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper - H y G", layout="wide")

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
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# (Aquí va tu lógica de login que ya funciona perfectamente)

if st.session_state.autenticado or True: # True para pruebas
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_pendientes': []
        })

    with st.sidebar:
        st.header("⚙️ Estrategia H y G")
        api_key = st.text_input("Binance API Key", type="password")
        api_secret = st.text_input("Binance Secret Key", type="password")
        
        st.markdown("---")
        # --- CONFIGURACIÓN RSI ---
        st.subheader("🛡️ Resguardo por RSI")
        rsi_limite = st.slider("Nivel RSI para asegurar ganancia", 50, 90, 70)
        
        st.subheader("📊 Malla de Niveles")
        niveles = st.number_input("Cantidad de Órdenes", 1, 20, 5)
        distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 1.0) / 100
        
        st.markdown("---")
        par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT", "PEPE/USDT"])
        leverage = st.slider("Apalancamiento", 1, 50, 20)
        monto_total = st.number_input("Inversión Total (USDT)", value=50.0)
        tp_global = st.slider("Take Profit Global (%)", 0.1, 5.0, 0.5) / 100

    st.subheader(f"Ejecución en Tiempo Real: {par}")
    bot_on = st.toggle("ACTIVAR ALGORITMO")

    if bot_on:
        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_actual = float(res['USD'])
            st.session_state.precios_hist.append(precio_actual)
            if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)
            
            rsi_actual = calcular_rsi(st.session_state.precios_hist)

            # --- CREAR MALLA ---
            if not st.session_state.posiciones and not st.session_state.ordenes_pendientes:
                monto_nivel = monto_total / niveles
                for n in range(niveles):
                    st.session_state.ordenes_pendientes.append({
                        'precio': precio_actual * (1 - (n * distancia)),
                        'monto': monto_nivel, 'ejecutada': False
                    })

            # --- EJECUTAR COMPRAS ---
            for orden in st.session_state.ordenes_pendientes:
                if not orden['ejecutada'] and precio_actual <= orden['precio']:
                    orden['ejecutada'] = True
                    st.session_state.posiciones.append({'entrada': precio_actual, 'monto': orden['monto']})
                    st.toast(f"🛒 Compra en nivel: ${precio_actual}")

            # --- LÓGICA DE CIERRE (RSI O TP) ---
            if st.session_state.posiciones:
                precio_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                target_tp = precio_promedio * (1 + tp_global)
                
                # REGLA DE ORO: SIEMPRE EN GANANCIA
                en_ganancia = precio_actual > precio_promedio

                # ¿Se cierra por TP o por RSI de resguardo?
                cierre_por_tp = precio_actual >= target_tp
                cierre_por_rsi = rsi_actual >= rsi_limite and en_ganancia

                if cierre_por_tp or cierre_por_rsi:
                    motivo = "TAKE PROFIT" if cierre_por_tp else "RESGUARDO RSI"
                    total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                    pnl = ((precio_actual - precio_promedio) / precio_promedio) * leverage * total_inv
                    
                    st.session_state.ganancia_acumulada += pnl
                    st.session_state.posiciones = []
                    st.session_state.ordenes_pendientes = []
                    
                    st.success(f"💰 Operación Cerrada ({motivo}) | Ganancia: +${pnl:.2f}")
                    time.sleep(2)
                    st.rerun()

            # --- DASHBOARD ---
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>Precio</div><div class='metric-value'>${precio_actual:,.4f}</div></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>RSI (14)</div><div class='metric-value'>{rsi_actual:.1f}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><div class='metric-label'>Niveles</div><div class='metric-value'>{len(st.session_state.posiciones)}/{niveles}</div></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='metric-card'><div class='metric-label'>PNL Acum.</div><div class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

            # --- GRÁFICO ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00')))
            for o in st.session_state.ordenes_pendientes:
                fig.add_hline(y=o['precio'], line_dash="dot", line_color="white" if not o['ejecutada'] else "#0088FF")
            if st.session_state.posiciones:
                fig.add_hline(y=target_tp, line_dash="dash", line_color="#F0B90B")
            
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            time.sleep(1.5); st.rerun()
        except: time.sleep(1); st.rerun()
    
