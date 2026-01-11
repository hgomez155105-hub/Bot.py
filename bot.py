import streamlit as st
import pandas as pd
import requests
import time
import os
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE SEGURIDAD ---
DB_FILE = "bot_history.csv" # Archivo para no perder datos

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Hora", "Moneda", "Evento", "Precio", "PNL", "Saldo_Total"])

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Enterprise", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.4); border: 2px solid #FFFFFF; border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ROBUSTA ---
if 'log_df' not in st.session_state:
    st.session_state.log_df = cargar_datos()
    # Recuperar último saldo si existe
    if not st.session_state.log_df.empty:
        st.session_state.saldo = float(st.session_state.log_df.iloc[0]['Saldo_Total'])
        st.session_state.ganancia_acumulada = st.session_state.log_df['PNL'].astype(float).sum()
    else:
        st.session_state.saldo = 1000.0
        st.session_state.ganancia_acumulada = 0.0

    st.session_state.update({
        'precios_hist': [], 'posiciones': [], 'moneda_activa': "SOL", 'x_est': 0.0
    })

# --- SIDEBAR (BINANCE STYLE) ---
st.sidebar.header("⚙️ BINANCE FUTURES CONFIG")
nueva_moneda = st.sidebar.selectbox("Par de Trading:", ["SOL/USDT", "BTC/USDT", "ETH/USDT", "PEPE/USDT"])
# Apalancamiento real de Binance (Máx 125x en BTC, 50x en otros)
max_leverage = 125 if "BTC" in nueva_moneda else 50
leverage = st.sidebar.slider("Apalancamiento (x)", 1, max_leverage, 10)
monto_trade = st.sidebar.number_input("Margen Inicial (USDT):", value=10.0)

st.sidebar.markdown("---")
dist_grid = st.sidebar.slider("Distancia de Rejilla (%)", 0.05, 5.0, 0.3) / 100
niveles_max = st.sidebar.slider("Límite de Rejillas:", 1, 20, 10)

# Botón de reset total (Cuidado)
if st.sidebar.button("🗑️ Borrar Historial y Reset"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()

encendido = st.sidebar.toggle("🚀 CONECTAR AL MERCADO", key="bot_activo")

# --- LÓGICA DE PERSISTENCIA AL CAMBIAR MONEDA ---
moneda_limpia = nueva_moneda.split("/")[0]
if moneda_limpia != st.session_state.moneda_activa:
    st.session_state.moneda_activa = moneda_limpia
    st.session_state.posiciones = []
    st.session_state.precios_hist = []
    st.rerun()

# --- UI PRINCIPAL ---
st.title(f"📊 ESCALADOR AI: {nueva_moneda}")

if st.session_state.bot_activo:
    try:
        # 1. API Precio
        url = f"https://min-api.cryptocompare.com/data/price?fsym={st.session_state.moneda_activa}&tsyms=USD"
        precio = float(requests.get(url, timeout=5).json()['USD'])
        st.session_state.precios_hist.append(precio)
        if len(st.session_state.precios_hist) > 50: st.session_state.precios_hist.pop(0)

        # 2. Lógica de Grid (Promediando precio)
        evento = "VIGILANDO"
        pnl_final = 0.0

        # Abrir primer nivel
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            st.session_state.saldo -= monto_trade
            evento = "🛒 OPEN LONG (L1)"
        
        # Abrir más niveles si cae
        elif len(st.session_state.posiciones) < niveles_max:
            if precio <= st.session_state.posiciones[-1]['precio'] * (1 - dist_grid):
                st.session_state.posiciones.append({'precio': precio, 'id': len(st.session_state.posiciones)+1})
                st.session_state.saldo -= monto_trade
                evento = f"🛒 ADD MARGIN (L{len(st.session_state.posiciones)})"

        # Venta por Profit
        for i, pos in enumerate(st.session_state.posiciones):
            if precio >= pos['precio'] * (1 + dist_grid):
                # Fórmula de Profit en Futuros Binance
                pnl_final = ((precio - pos['precio']) / pos['precio']) * leverage * monto_trade
                st.session_state.saldo += (monto_trade + pnl_final)
                st.session_state.ganancia_acumulada += pnl_final
                st.session_state.posiciones.pop(i)
                evento = f"💰 CLOSE LONG (L{pos['id']})"
                
                # GUARDAR EN DISCO INMEDIATAMENTE
                hora_act = datetime.now().strftime("%H:%M:%S")
                nuevo_dato = pd.DataFrame([{"Hora": hora_act, "Moneda": nueva_moneda, "Evento": evento, "Precio": precio, "PNL": pnl_final, "Saldo_Total": st.session_state.saldo}])
                st.session_state.log_df = pd.concat([nuevo_dato, st.session_state.log_df]).reset_index(drop=True)
                guardar_datos(st.session_state.log_df)
                break

        # 3. Dashboard
        c1, c2, c3 = st.columns(3)
        c1.metric("MARK PRICE", f"${precio:,.4f}")
        c2.metric("PROFIT TOTAL", f"${st.session_state.ganancia_acumulada:,.2f}")
        c3.metric("WALLET BALANCE", f"${st.session_state.saldo:,.2f}")

        # 4. Gráfico de Escala Real
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=2), name="Live Price"))
        
        for p in st.session_state.posiciones:
            fig.add_hline(y=p['precio'], line_color="white", annotation_text="ENTRY")
            fig.add_hline(y=p['precio']*(1+dist_grid), line_color="gold", line_dash="dash", annotation_text="TAKE PROFIT")
        
        if len(st.session_state.posiciones) < niveles_max:
            fig.add_hline(y=st.session_state.posiciones[-1]['precio']*(1-dist_grid), line_color="red", line_dash="dot", annotation_text="NEXT BUY")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(color="white"))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📋 REGISTRO PERMANENTE (bot_history.csv)")
        st.dataframe(st.session_state.log_df.head(20), use_container_width=True)

        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.error(f"Conexión perdida... Reintentando. Error: {e}")
        time.sleep(2)
        st.rerun()
        
