import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Enterprise", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    div[data-testid="metric-container"] { 
        background-color: #1E2329; border: 1px solid #474D57; border-radius: 10px;
    }
    h1, h2, h3, p, span, label { color: #EAECEF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'ganancia_acumulada': 0.0, # Línea específica para lo ganado
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL", "Modo"])
    })

# --- SIDEBAR ---
st.sidebar.title("🚀 CONFIGURACIÓN PRO")
modo = st.sidebar.radio("Entorno:", ["🧪 DEMO", "🔥 REAL"])
es_real = modo == "🔥 REAL"

par = st.sidebar.selectbox("Activo:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("Apalancamiento", 1, 50, 20)
monto_nivel = st.sidebar.number_input("Margen por Nivel (USDT)", value=10.0)
dist_grid = st.sidebar.slider("Distancia Profit (%)", 0.1, 5.0, 0.7) / 100

if st.sidebar.button("🚨 CIERRE TOTAL / RESET", type="primary"):
    st.session_state.posiciones = []
    st.session_state.ganancia_acumulada = 0.0
    st.rerun()

bot_on = st.sidebar.toggle("⚡ ACTIVAR BOT")

# --- FUNCIONES ---
def obtener_precio(symbol):
    coin = symbol.split("/")[0]
    res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
    return float(res['USD'])

# --- UI PRINCIPAL ---
st.title(f"ESTRATEGIA AGRESIVA: {par}")

if bot_on:
    try:
        precio = obtener_precio(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # RSI Simulado (Ajustado para salidas en 70)
        rsi = 35 + (precio % 1 * 40) 

        # 1. ENTRADA AGRESIVA
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto_nivel
        
        # 2. SALIDA POR PROFIT O RSI 70
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            
            # Criterio: Profit objetivo O RSI >= 70
            if (precio >= target or rsi >= 70) and precio > pos['precio']:
                pnl = ((precio - pos['precio']) / pos['precio']) * leverage * monto_nivel
                
                # Actualizar Balances
                if not es_real:
                    st.session_state.saldo_demo += (monto_nivel + pnl)
                st.session_state.ganancia_acumulada += pnl
                
                # Log con HORA LOCAL
                hora_local = datetime.now().strftime("%H:%M:%S")
                new_log = pd.DataFrame([{"Hora": hora_local, "Evento": f"💰 VENTA N{pos['id']}", "Precio": precio, "PNL": f"${pnl:.2f}", "Modo": modo}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                
                st.session_state.posiciones.pop(i)
                st.rerun()
                break

        # --- PANEL DE MÉTRICAS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        c2.metric("RSI ESTRATEGIA", f"{rsi:.1f}")
        c3.metric("BILLETERA USDT", f"${st.session_state.saldo_demo:,.2f}")
        c4.metric("GANANCIA ACUMULADA", f"${st.session_state.ganancia_acumulada:,.2f}", delta=f"{pnl:.2f}" if 'pnl' in locals() else None)

        # --- GRÁFICO ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00')))
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", annotation_text="ENTRY")
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="gold", line_dash="dash", annotation_text="TARGET")
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, yaxis=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(st.session_state.log_df.head(15), use_container_width=True)

        time.sleep(2)
        st.rerun()

    except Exception:
        time.sleep(1)
        st.rerun()
