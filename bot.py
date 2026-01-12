import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide")

# --- LÓGICA RSI ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    return 100 - (100 / (1 + (avg_gain / (avg_loss if avg_loss != 0 else 0.001))))

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 10px; padding: 10px; text-align: center;
    }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #F0B90B; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
        'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 'ultimo_par': ""
    })

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    par = st.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
    
    # RESET TOTAL AL CAMBIAR MONEDA
    if par != st.session_state.ultimo_par:
        st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
        st.rerun()

    lev = st.slider("Apalancamiento", 1, 50, 20)
    niveles = st.number_input("Niveles de Malla", 1, 15, 5)
    distancia = st.slider("Distancia (%)", 0.1, 2.0, 0.5) / 100
    monto_total = st.number_input("Inversión Total (USDT)", 10.0, 5000.0, 100.0)
    tp_global = st.slider("Take Profit Global (%)", 0.1, 5.0, 1.0) / 100
    rsi_trigger = st.slider("RSI Compra", 10, 50, 30)

# --- PANEL PRINCIPAL ---
st.title(f"Panel: {par}")
bot_on = st.toggle("EJECUTAR ALGORITMO")

if bot_on:
    try:
        # 1. Obtener Precio Real
        coin = par.split('/')[0]
        res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
        precio = float(res['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)

        rsi_actual = calcular_rsi(st.session_state.precios_hist)

        # 2. Lógica de Malla y Descuento de Saldo
        if not st.session_state.posiciones and not st.session_state.ordenes_malla:
            if rsi_actual <= rsi_trigger:
                monto_nivel = monto_total / niveles
                for i in range(niveles):
                    p_nivel = precio * (1 - (i * distancia))
                    st.session_state.ordenes_malla.append({'precio': p_nivel, 'monto': monto_nivel, 'estado': 'pendiente'})

        # Ejecución de compras
        for orden in st.session_state.ordenes_malla:
            if orden['estado'] == 'pendiente' and precio <= orden['precio']:
                if st.session_state.saldo_demo >= orden['monto']:
                    orden['estado'] = 'ejecutada'
                    st.session_state.posiciones.append({'entrada': precio, 'monto': orden['monto']})
                    st.session_state.saldo_demo -= orden['monto'] # DESCUENTO AQUÍ
                else:
                    st.error("SALDO DEMO INSUFICIENTE")

        # 3. Lógica de Cierre (Profit)
        if st.session_state.posiciones:
            p_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
            p_profit = p_promedio * (1 + tp_global)
            
            if precio >= p_profit:
                total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                ganancia = (total_inv * tp_global) * lev
                st.session_state.saldo_demo += (total_inv + ganancia)
                st.session_state.ganancia_acumulada += ganancia
                st.session_state.posiciones = []
                st.session_state.ordenes_malla = []
                st.balloons()

        # --- DASHBOARD ---
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='metric-card'>Precio<br><span class='metric-value'>${precio:,.2f}</span></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'>Disponible<br><span class='metric-value'>${st.session_state.saldo_demo:,.2f}</span></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'>PNL<br><span class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</span></div>", unsafe_allow_html=True)

        # --- GRÁFICO CON LÍNEAS DE COMPRA Y PROFIT ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3)))

        # Dibujar niveles de la malla (LÍNEAS DE COMPRA)
        for orden in st.session_state.ordenes_malla:
            color = "rgba(0, 255, 0, 0.8)" if orden['estado'] == 'ejecutada' else "rgba(150, 150, 150, 0.5)"
            fig.add_hline(y=orden['precio'], line_dash="dash", line_color=color, annotation_text=" NIVEL COMPRA")

        # Dibujar Take Profit (LÍNEA CIAN)
        if st.session_state.posiciones:
            p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
            fig.add_hline(y=p_prom * (1 + tp_global), line_color="#00FFFF", line_width=2, annotation_text=" TAKE PROFIT")

        fig.update_layout(height=500, margin=dict(l=0,r=0,b=0,t=0), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"RSI: {rsi_actual:.2f} | Esperando RSI < {rsi_trigger} para comprar")
        time.sleep(2); st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(2); st.rerun()
