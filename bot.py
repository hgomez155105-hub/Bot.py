import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Grid Pro", layout="wide")

# --- ESTILO MAC / VERDE MILITAR ---
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.8rem !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 1px solid #FFFFFF; border-radius: 10px; padding: 10px;
    }
    .stDataFrame { background-color: rgba(0,0,0,0.5) !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA (SESSION STATE) ---
if 'log_df' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 
        'ganancia_acumulada': 0.0,
        'precios_hist': [], 
        'posiciones': [], # Lista de diccionarios con niveles abiertos
        'x_est': 0.0, 
        'p_cov': 1.0,
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL Nivel"])
    })

# --- SIDEBAR (PANEL DE CONTROL) ---
st.sidebar.header("🕹️ CONTROL DE GRID")
moneda = st.sidebar.selectbox("Moneda:", ["BTC", "SOL", "ETH", "XRP", "ADA"])
apalancamiento = st.sidebar.slider("Apalancamiento (Leverage):", 1, 50, 10)
monto_por_nivel = st.sidebar.number_input("Monto por Nivel (USD):", value=50.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 PARÁMETROS DE REJILLA")
distancia_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.05, 2.0, 0.2) / 100
niveles_max = st.sidebar.slider("Máximo de niveles (Grids):", 1, 20, 7)

st.sidebar.markdown("---")
encendido = st.sidebar.toggle("🚀 ENCENDER ALGORITMO", key="bot_activo")

# --- FUNCIÓN FILTRO DE IA (KALMAN) ---
def aplicar_kalman(medicion, est_anterior, cov_anterior):
    R, Q = 0.01**2, 0.001**2
    est_prior = est_anterior
    cov_prior = cov_anterior + Q
    ganancia = cov_prior / (cov_prior + R)
    nueva_est = est_prior + ganancia * (medicion - est_prior)
    nueva_cov = (1 - ganancia) * cov_prior
    return nueva_est, nueva_cov

# --- UI PRINCIPAL ---
st.title(f"📊 GRID BOT {apalancamiento}x : {moneda}")

if st.session_state.bot_activo:
    try:
        # 1. Obtener precio en tiempo real
        url = f"https://min-api.cryptocompare.com/data/price?fsym={moneda}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        precio = float(res['USD'])
        
        # 2. Actualizar IA y Gráfico
        if st.session_state.x_est == 0.0: st.session_state.x_est = precio
        st.session_state.x_est, st.session_state.p_cov = aplicar_kalman(precio, st.session_state.x_est, st.session_state.p_cov)
        
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)

        # 3. LÓGICA DE REJILLAS (GRID)
        evento = "VIGILANDO"
        pnl_actual_trade = 0.0
        
        # A. Abrir primer nivel si no hay posiciones
        if not st.session_state.posiciones:
            nueva_pos = {'precio': precio, 'monto': monto_por_nivel, 'id': 1}
            st.session_state.posiciones.append(nueva_pos)
            st.session_state.saldo -= monto_por_nivel
            evento = "🛒 NIVEL 1 ABIERTO"
        
        # B. Lógica de Apertura de niveles inferiores (Promedio)
        elif len(st.session_state.posiciones) < niveles_max:
            ultimo_precio = st.session_state.posiciones[-1]['precio']
            # Solo compra si el precio bajó la distancia configurada respecto al último nivel
            if precio <= ultimo_precio * (1 - distancia_grid):
                nueva_pos = {'precio': precio, 'monto': monto_por_nivel, 'id': len(st.session_state.posiciones) + 1}
                st.session_state.posiciones.append(nueva_pos)
                st.session_state.saldo -= monto_por_nivel
                evento = f"🛒 NIVEL {len(st.session_state.posiciones)} ABIERTO"

        # C. Lógica de Venta (Cerrar niveles con ganancia)
        for i, pos in enumerate(st.session_state.posiciones):
            dif_perc = (precio - pos['precio']) / pos['precio']
            # Vende si el precio subió la distancia configurada
            if dif_perc >= distancia_grid:
                profit_bruto = (dif_perc * apalancamiento) * pos['monto']
                st.session_state.saldo += (pos['monto'] + profit_bruto)
                st.session_state.ganancia_acumulada += profit_bruto
                st.session_state.posiciones.pop(i)
                evento = f"💰 NIVEL {pos['id']} CERRADO"
                pnl_actual_trade = profit_bruto
                break # Evitamos errores de índice al borrar

        # 4. MÉTRICAS DE ESTADO
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        c2.metric("GANANCIA ACUM.", f"${st.session_state.ganancia_acumulada:.2f}")
        c3.metric("BILLETERA (CASH)", f"${st.session_state.saldo:,.2f}")

        # PNL Flotante (Suma de todos los niveles abiertos multiplicada por apalancamiento)
        pnl_flotante = sum([((precio - p['precio'])/p['precio'] * apalancamiento * p['monto']) for p in st.session_state.posiciones])
        
        st.markdown(f"### ⚡ ESTADO DEL GRID: {len(st.session_state.posiciones)} niveles activos")
        col_f1, col_f2 = st.columns(2)
        col_f1.metric("PNL FLOTANTE (SIN CERRAR)", f"${pnl_flotante:.2f}")
        col_f2.metric("MARGEN EN USO", f"${len(st.session_state.posiciones) * monto_por_nivel:.2f}")

        # 5. GRÁFICO CON LÍNEAS DE REJILLA
        
        fig = go.Figure()
        # Línea de precio
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', name='Precio', line=dict(color='#00FF00', width=2)))
        # Línea de IA
        fig.add_trace(go.Scatter(y=[st.session_state.x_est]*len(st.session_state.precios_hist), mode='lines', name='IA Trend', line=dict(color='#FF00FF', dash='dot')))
        
        # Dibujar niveles abiertos (Blanco) y su objetivo de venta (Oro)
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_dash="solid", line_color="white", annotation_text=f"Nivel {p['id']}")
            fig.add_hline(y=p['precio']*(1+distancia_grid), line_dash="dash", line_color="gold", annotation_text="VENDER")

        # Dibujar previsión de dónde abrirá el siguiente nivel si el precio cae (Rojo)
        if len(st.session_state.posiciones) < niveles_max:
            next_buy = st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid)
            fig.add_hline(y=next_buy, line_dash="dot", line_color="red", annotation_text="PROX. COMPRA")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, font=dict(color="white"), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # 6. HISTORIAL DE EVENTOS
        hora = datetime.now().strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "PNL Nivel": f"${pnl_actual_trade:.2f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
        
        st.markdown("### 📋 LOG DE OPERACIONES")
        st.dataframe(st.session_state.log_df.head(20), use_container_width=True)

        time.sleep(4)
        st.rerun()

    except Exception as e:
        st.warning(f"Sincronizando datos... {e}")
        time.sleep(2)
        st.rerun()
else:
    st.info("👋 El simulador de Rejillas está apagado. Ajusta tus niveles y dale a ENCENDER.")
