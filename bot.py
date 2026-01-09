import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Grid Sim", layout="wide")

# CSS: Verde Militar
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 1px solid #FFFFFF; border-radius: 10px; padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'log_df' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_acumulada': 0.0,
        'precios_hist': [], 'kalman_hist': [],
        'posiciones': [], # Lista de compras en rejilla
        'x_est': 0.0, 'p_cov': 1.0,
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "Poro"])
    })

# --- SIDEBAR ---
st.sidebar.header("🕹️ CONFIGURACIÓN PRO")
moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "XRP"])
apalancamiento = st.sidebar.slider("Apalancamiento (Leverage):", 1, 20, 10)
monto_por_rejilla = st.sidebar.number_input("Inversión por Nivel (USD):", value=20.0)

st.sidebar.subheader("📐 AJUSTE DE REJILLA (GRID)")
distancia_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.1, 2.0, 0.5) / 100
niveles_max = st.sidebar.slider("Máximo de niveles:", 3, 10, 5)

encendido = st.sidebar.toggle("🚀 ENCENDER SIMULADOR", key="bot_activo")

# --- UI PRINCIPAL ---
st.title(f"📊 GRID TRADING SIM: {moneda} {apalancamiento}x")

if st.session_state.bot_activo:
    try:
        # 1. Obtener precio
        url = f"https://min-api.cryptocompare.com/data/price?fsym={moneda}&tsyms=USD"
        precio = float(requests.get(url).json()['USD'])
        
        # 2. IA Kalman para tendencia
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        R, Q = 0.01**2, 0.001**2
        cov_prior = st.session_state.p_cov + Q
        ganancia_k = cov_prior / (cov_prior + R)
        st.session_state.x_est = st.session_state.x_est + ganancia_k * (precio - st.session_state.x_est)
        st.session_state.p_cov = (1 - ganancia_k) * cov_prior
        
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # 3. LÓGICA DE REJILLAS (GRID)
        evento = "VIGILANDO"
        
        # ¿Hay que abrir una nueva rejilla? (Si el precio baja la distancia configurada)
        puede_comprar = len(st.session_state.posiciones) < niveles_max
        if puede_comprar:
            if not st.session_state.posiciones or precio < st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid):
                nueva_pos = {'precio': precio, 'monto': monto_por_rejilla}
                st.session_state.posiciones.append(nueva_pos)
                st.session_state.saldo -= monto_por_rejilla
                evento = f"🛒 REJILLA {len(st.session_state.posiciones)} OPEN"

        # ¿Hay que cerrar alguna rejilla? (Si el precio sube la distancia configurada)
        for i, pos in enumerate(st.session_state.posiciones):
            dif_precio = (precio - pos['precio']) / pos['precio']
            # Aplicamos apalancamiento a la ganancia/pérdida
            profit_simulado = (dif_precio * apalancamiento) * pos['monto']
            
            if dif_precio >= distancia_grid: # Vendemos este nivel
                st.session_state.saldo += (pos['monto'] + profit_simulado)
                st.session_state.ganancia_acumulada += profit_simulado
                st.session_state.posiciones.pop(i)
                evento = "💰 REJILLA CLOSE (PROFIT)"
                break

        # 4. MÉTRICAS CON APALANCAMIENTO
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("NIVELES ABIERTOS", len(st.session_state.posiciones))
        # PNL Flotante (lo que vas perdiendo/ganando mientras estás adentro)
        pnl_flotante = sum([( (precio - p['precio'])/p['precio'] * apalancamiento * p['monto'] ) for p in st.session_state.posiciones])
        c3.metric("PNL FLOTANTE", f"${pnl_flotante:.2f}")

        # 5. GRÁFICO DE REJILLAS
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', name='Precio', line=dict(color='#00FF00')))
        # Dibujar líneas de las rejillas activas
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_dash="dot", line_color="white")
            fig.add_hline(y=p['precio']*(1+distancia_grid), line_dash="dash", line_color="gold")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # 6. ESTADÍSTICAS Y LOG
        st.write(f"💵 Billetera: ${st.session_state.saldo:,.2f} | 📈 Ganancia Realizada: ${st.session_state.ganancia_acumulada:,.2f}")
        
        hora = datetime.now().strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "PNL": f"${pnl_flotante:.2f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)

        time.sleep(4)
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(2)
        st.rerun()
        
