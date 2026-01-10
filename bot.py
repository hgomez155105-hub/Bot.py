import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Grid Pro", layout="wide")

# --- ESTADO DE SESIÓN ---
if 'moneda_activa' not in st.session_state:
    st.session_state.moneda_activa = "BTC"

def reset_bot():
    st.session_state.precios_hist = []
    st.session_state.posiciones = []
    st.session_state.x_est = 0.0
    st.session_state.p_cov = 1.0

if 'precios_hist' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_acumulada': 0.0,
        'precios_hist': [], 'posiciones': [], 'x_est': 0.0, 'p_cov': 1.0,
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- SIDEBAR ---
st.sidebar.header("🕹️ PANEL DE CONTROL")
nueva_moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "XRP", "ADA"])

if nueva_moneda != st.session_state.moneda_activa:
    st.session_state.moneda_activa = nueva_moneda
    reset_bot()
    st.rerun()

apalancamiento = st.sidebar.slider("Apalancamiento (Leverage):", 1, 50, 10)
monto_por_nivel = st.sidebar.number_input("Monto por Nivel (USD):", value=50.0)
distancia_grid = st.sidebar.slider("Distancia Grid (%)", 0.05, 1.0, 0.2) / 100
niveles_max = st.sidebar.slider("Máximo de Niveles:", 1, 15, 7)

st.sidebar.markdown("---")
encendido = st.sidebar.toggle("🚀 ENCENDER ALGORITMO", key="bot_activo")

# --- UI DINÁMICA ---
st.title(f"📊 GRID BOT: {st.session_state.moneda_activa} {apalancamiento}x")

if st.session_state.bot_activo:
    try:
        # 1. Obtener precio
        url = f"https://min-api.cryptocompare.com/data/price?fsym={st.session_state.moneda_activa}&tsyms=USD"
        precio = float(requests.get(url, timeout=5).json()['USD'])
        
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 40: st.session_state.precios_hist.pop(0)

        # 2. Lógica de Rejillas
        evento = "VIGILANDO"
        pnl_realizado = 0.0
        cerca_de_venta = False

        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            st.session_state.saldo -= monto_por_nivel
            evento = "🛒 NIVEL 1 OPEN"
        elif len(st.session_state.posiciones) < niveles_max:
            if precio <= st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid):
                st.session_state.posiciones.append({'precio': precio, 'id': len(st.session_state.posiciones)+1})
                st.session_state.saldo -= monto_por_nivel
                evento = f"🛒 NIVEL {len(st.session_state.posiciones)} OPEN"

        # 3. Alerta de Venta y Cierre
        for i, pos in enumerate(st.session_state.posiciones):
            objetivo = pos['precio'] * (1 + distancia_grid)
            # Si el precio está a menos del 0.05% del objetivo
            if precio >= objetivo * 0.9995 and precio < objetivo:
                cerca_de_venta = True
            
            if precio >= objetivo:
                dif = (precio - pos['precio']) / pos['precio']
                pnl_realizado = (dif * apalancamiento) * monto_por_nivel
                st.session_state.saldo += (monto_por_nivel + pnl_realizado)
                st.session_state.ganancia_acumulada += pnl_realizado
                st.session_state.posiciones.pop(i)
                evento = f"💰 NIVEL {pos['id']} PROFIT"
                break

        # --- CSS DINÁMICO PARA ALERTA ---
        color_fondo = "rgba(255, 165, 0, 0.4)" if cerca_de_venta else "rgba(0,0,0,0.3)"
        st.markdown(f"""
            <style>
            .stApp {{ background-color: #4B5320 !important; }}
            div[data-testid="metric-container"] {{ 
                background-color: {color_fondo} !important; 
                border: 2px solid {'#FFD700' if cerca_de_venta else '#FFFFFF'};
                transition: 0.5s;
            }}
            </style>
            """, unsafe_allow_html=True)

        if cerca_de_venta:
            st.warning("⚠️ ¡ALERTA! PRECIO EN ZONA DE TOMA DE GANANCIAS")

        # 4. Métricas y Gráfico
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        c2.metric("GANANCIA TOTAL", f"${st.session_state.ganancia_acumulada:.2f}")
        c3.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        # Gráfico con Escala Dinámica
        y_min = min(st.session_state.precios_hist) * 0.999
        y_max = max(st.session_state.precios_hist) * 1.001
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=3)))
        
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", line_dash="solid")
            fig.add_hline(y=p['precio']*(1+distancia_grid), line_color="gold", line_dash="dash")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400,
                          margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(range=[y_min, y_max], color="white"))
        st.plotly_chart(fig, use_container_width=True)

        # 5. Log
        hora = datetime.now().strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "PNL": f"${pnl_realizado:.2f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)

        time.sleep(3)
        st.rerun()

    except Exception as e:
        time.sleep(2)
        st.rerun()
            
