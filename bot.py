import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA (Optimizado para móvil) ---
st.set_page_config(page_title="AI Scalper Pro", layout="centered")

# --- ESTILO CSS PROFESIONAL (UX de Aplicación Móvil) ---
st.markdown("""
    <style>
    /* Fondo y tipografía */
    .stApp { background-color: #0B0E11 !important; }
    h1, h2, h3, p, span, label { color: #EAECEF !important; font-family: 'Inter', sans-serif; }
    
    /* Tarjetas de métricas tipo App */
    .metric-card {
        background: #1E2329;
        border: 1px solid #474D57;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        text-align: center;
    }
    .metric-label { font-size: 0.8rem; color: #848E9C; margin-bottom: 5px; }
    .metric-value { font-size: 1.4rem; font-weight: bold; color: #00FFAA; }
    
    /* Botones grandes para dedos */
    .stButton>button {
        width: 100%;
        height: 50px;
        border-radius: 10px;
        font-size: 1rem !important;
        font-weight: bold !important;
        margin-top: 10px;
    }
    
    /* Esconder menú de Streamlit para que parezca App nativa */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'ganancia_acumulada': 0.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- BARRA LATERAL (Ajustes) ---
with st.sidebar:
    st.header("⚙️ CONFIGURACIÓN")
    modo = st.radio("Modo:", ["🧪 DEMO", "🔥 REAL"])
    par = st.selectbox("Moneda:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
    leverage = st.slider("Apalancamiento", 1, 50, 20)
    monto_nivel = st.number_input("Margen (USDT)", value=10.0)
    dist_grid = st.slider("Profit (%)", 0.1, 5.0, 0.7) / 100
    
    st.markdown("---")
    if st.button("🚨 CIERRE DE EMERGENCIA", type="primary"):
        st.session_state.posiciones = []
        st.rerun()

# --- LÓGICA DE TRADING ---
def obtener_precio(symbol):
    coin = symbol.split("/")[0]
    res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
    return float(res['USD'])

# --- INTERFAZ MÓVIL PRINCIPAL ---
st.markdown(f"<h3 style='text-align: center;'>🚀 AI SCALPER: {par}</h3>", unsafe_allow_html=True)

# Botón de encendido grande
bot_on = st.toggle("ENCENDER ALGORITMO", key="bot_active")

if bot_on:
    try:
        precio = obtener_precio(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 30: st.session_state.precios_hist.pop(0)
        
        rsi = 35 + (precio % 1 * 40) # RSI Simulado

        # Lógica Agresiva
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            st.session_state.saldo_demo -= monto_nivel

        # Lógica de Salida
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            if (precio >= target or rsi >= 70) and precio > pos['precio']:
                pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto_nivel
                st.session_state.saldo_demo += (monto_nivel + pnl)
                st.session_state.ganancia_acumulada += pnl
                
                new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": "VENTA", "Precio": precio, "PNL": f"${pnl:.2f}"}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                st.session_state.posiciones.pop(i)
                st.rerun()

        # --- DISEÑO DE TARJETAS MÓVILES ---
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>PRECIO</div><div class='metric-value'>${precio:,.2f}</div></div>", unsafe_allow_html=True)
            st.markdown(f<div class='metric-card'><div class='metric-label'>BILLETERA</div><div class='metric-value'>${st.session_state.saldo_demo:,.1f}</div></div>", unsafe_allow_html=True)
        with col_b:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>RSI</div><div class='metric-value'>{rsi:.1f}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card'><div class='metric-label'>PROFIT TOTAL</div><div class='metric-value' style='color:#F0B90B;'>${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

        # --- GRÁFICO SIMPLIFICADO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00', width=3)))
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", line_width=1)
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="gold", line_dash="dash")
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0,r=0,t=10,b=0), yaxis=dict(showgrid=False, color="white"))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Log pequeño para móvil
        st.dataframe(st.session_state.log_df.head(5), use_container_width=True)

        time.sleep(2)
        st.rerun()

    except Exception:
        time.sleep(1)
        st.rerun()
else:
    st.info("👋 Bot en pausa. Configura y activa para empezar.")
        
