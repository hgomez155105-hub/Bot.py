import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Scalper Agresivo", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    h1, h2, h3, p, span, label { color: #EAECEF !important; }
    div[data-testid="metric-container"] { 
        background-color: #1E2329; border: 1px solid #474D57; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo_demo' not in st.session_state:
    st.session_state.update({
        'saldo_demo': 1000.0,
        'posiciones': [],
        'precios_hist': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL", "Modo"])
    })

# --- SIDEBAR ---
st.sidebar.title("🚀 FUTUROS AGRESIVO")
modo = st.sidebar.radio("Entorno:", ["🧪 DEMO", "🔥 REAL"])
es_real = modo == "🔥 REAL"

st.sidebar.markdown("---")
par = st.sidebar.selectbox("Moneda:", ["SOL/USDT", "BTC/USDT", "ETH/USDT"])
leverage = st.sidebar.slider("Apalancamiento", 1, 50, 20)
monto_nivel = st.sidebar.number_input("Margen por Nivel (USDT)", value=10.0)

st.sidebar.subheader("📐 REJILLA")
dist_grid = st.sidebar.slider("Distancia entre niveles (%)", 0.1, 2.0, 0.4) / 100
max_niveles = st.sidebar.slider("Máximo de niveles", 1, 15, 8)

if st.sidebar.button("🚨 CIERRE TOTAL / RESET", type="primary"):
    st.session_state.posiciones = []
    st.rerun()

bot_on = st.sidebar.toggle("⚡ ACTIVAR BOT")

# --- LÓGICA ---
def obtener_precio(symbol):
    coin = symbol.split("/")[0]
    res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
    return float(res['USD'])

# --- UI ---
st.title(f"BOT AGRESIVO: {par} {leverage}x")

if bot_on:
    try:
        precio = obtener_precio(par)
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # RSI para promedios y salidas (Simulado)
        rsi = 30 + (precio % 1 * 40) 

        evento = "VIGILANDO"
        pnl_realizado = 0.0

        # 1. ENTRADA AGRESIVA (Nivel 1 sin esperar RSI)
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            if not es_real: st.session_state.saldo_demo -= monto_nivel
            evento = "🚀 ENTRADA INICIAL"

        # 2. REJILLA CON RSI (Niveles 2+ solo si RSI es bajo)
        elif 0 < len(st.session_state.posiciones) < max_niveles:
            ultimo_p = st.session_state.posiciones[-1]['precio']
            # Compra si el precio cayó Y el RSI está bajo (<45)
            if precio <= ultimo_p * (1 - dist_grid) and rsi < 45:
                nuevo_id = len(st.session_state.posiciones) + 1
                st.session_state.posiciones.append({'precio': precio, 'id': nuevo_id})
                if not es_real: st.session_state.saldo_demo -= monto_nivel
                evento = f"🛒 PROMEDIO N{nuevo_id}"

        # 3. CIERRE DE NIVELES (Profit o RSI > 60)
        for i, pos in enumerate(st.session_state.posiciones):
            target = pos['precio'] * (1 + dist_grid)
            if (precio >= target or rsi >= 60) and precio > pos['precio']:
                pnl_realizado = ((precio - pos['precio']) / pos['precio']) * leverage * monto_nivel
                if not es_real: st.session_state.saldo_demo += (monto_nivel + pnl_realizado)
                
                evento = f"💰 PROFIT N{pos['id']}"
                new_log = pd.DataFrame([{"Hora": datetime.now().strftime("%H:%M:%S"), "Evento": evento, "Precio": precio, "PNL": f"${pnl_realizado:.2f}", "Modo": modo}])
                st.session_state.log_df = pd.concat([new_log, st.session_state.log_df]).reset_index(drop=True)
                st.session_state.posiciones.pop(i)
                st.rerun() # Reiniciar para evaluar nueva entrada
                break

        # DASHBOARD
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PRECIO", f"${precio:,.2f}")
        c2.metric("RSI", f"{rsi:.1f}")
        c3.metric("NIVELES ACTIVOS", len(st.session_state.posiciones))
        c4.metric("SALDO DEMO", f"${st.session_state.saldo_demo:,.2f}")

        # GRÁFICO
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00')))
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", annotation_text=f"N{p['id']}")
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="gold", line_dash="dash")
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, yaxis=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)

        time.sleep(2)
        st.rerun()

    except Exception as e:
        time.sleep(2)
        st.rerun()
