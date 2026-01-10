import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper Grid Pro", layout="wide")

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #4B5320 !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; font-weight: 800 !important; }
    div[data-testid="metric-container"] { 
        background-color: rgba(0,0,0,0.3); border: 1px solid #FFFFFF; border-radius: 10px; padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ESTADO DE SESIÓN ---
if 'moneda_activa' not in st.session_state:
    st.session_state.moneda_activa = "SOL"

def reset_bot():
    st.session_state.precios_hist = []
    st.session_state.posiciones = []

if 'precios_hist' not in st.session_state:
    st.session_state.update({
        'saldo': 1000.0, 'ganancia_acumulada': 0.0,
        'precios_hist': [], 'posiciones': [],
        'log_df': pd.DataFrame(columns=["Hora", "Evento", "Precio", "PNL"])
    })

# --- SIDEBAR ---
st.sidebar.header("🕹️ PANEL DE CONTROL")
nueva_moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "XRP", "ADA"])

if nueva_moneda != st.session_state.moneda_activa:
    st.session_state.moneda_activa = nueva_moneda
    reset_bot()
    st.rerun()

apalancamiento = st.sidebar.slider("Apalancamiento:", 1, 50, 19)
monto_por_nivel = st.sidebar.number_input("Monto por Nivel (USD):", value=2.0)
distancia_grid = st.sidebar.slider("Distancia Grid (%)", 0.05, 2.0, 0.5) / 100
niveles_max = st.sidebar.slider("Máximo de Niveles:", 1, 15, 6)

encendido = st.sidebar.toggle("🚀 ENCENDER ALGORITMO", key="bot_activo")

# --- UI PRINCIPAL ---
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

        # Abrir nivel inicial
        if not st.session_state.posiciones:
            st.session_state.posiciones.append({'precio': precio, 'id': 1})
            st.session_state.saldo -= monto_por_nivel
            evento = "🛒 NIVEL 1 OPEN"
        
        # Abrir niveles adicionales (Promedio)
        elif len(st.session_state.posiciones) < niveles_max:
            if precio <= st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid):
                st.session_state.posiciones.append({'precio': precio, 'id': len(st.session_state.posiciones)+1})
                st.session_state.saldo -= monto_por_nivel
                evento = f"🛒 NIVEL {len(st.session_state.posiciones)} OPEN"

        # Cierre por Profit
        for i, pos in enumerate(st.session_state.posiciones):
            objetivo_venta = pos['precio'] * (1 + distancia_grid)
            if precio >= objetivo_venta:
                dif = (precio - pos['precio']) / pos['precio']
                pnl_realizado = (dif * apalancamiento) * monto_por_nivel
                st.session_state.saldo += (monto_por_nivel + pnl_realizado)
                st.session_state.ganancia_acumulada += pnl_realizado
                st.session_state.posiciones.pop(i)
                evento = f"💰 NIVEL {pos['id']} PROFIT"
                break
            # Alerta visual si está cerca del objetivo
            if precio >= objetivo_venta * 0.9997: cerca_de_venta = True

        # 3. Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("PRECIO ACTUAL", f"${precio:,.2f}")
        c2.metric("GANANCIA TOTAL", f"${st.session_state.ganancia_acumulada:.2f}")
        c3.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        # 4. Gráfico con Líneas de Umbral
        y_min, y_max = min(st.session_state.precios_hist) * 0.998, max(st.session_state.precios_hist) * 1.002
        fig = go.Figure()
        
        # Línea de precio real
        fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines+markers', line=dict(color='#00FF00', width=3), name="Precio"))

        # --- DIBUJAR UMBRALES ---
        for p in st.session_state.posiciones:
            # Línea de Compra Realizada (Blanca)
            fig.add_hline(y=p['precio'], line_color="white", line_width=1, annotation_text=f"Nivel {p['id']}")
            # Línea de Venta Objetivo (Dorada)
            fig.add_hline(y=p['precio']*(1+distancia_grid), line_color="gold", line_dash="dash", annotation_text="VENDER")

        # Línea de Próxima Compra (Roja) - Si hay espacio en la rejilla
        if len(st.session_state.posiciones) < niveles_max:
            prox_compra = st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid)
            fig.add_hline(y=prox_compra, line_color="red", line_dash="dot", annotation_text="PRÓX. COMPRA")

        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400,
                          margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(range=[y_min, y_max], color="white"))
        
        if cerca_de_venta: st.warning("⚠️ ¡ZONA DE VENTA ALCANZADA!")
        st.plotly_chart(fig, use_container_width=True)

        # 5. Log de Operaciones
        hora = datetime.now().strftime("%H:%M:%S")
        nuevo_log = pd.DataFrame([{"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "PNL": f"${pnl_realizado:.4f}"}])
        st.session_state.log_df = pd.concat([nuevo_log, st.session_state.log_df]).reset_index(drop=True)
        st.dataframe(st.session_state.log_df.head(10), use_container_width=True)

        time.sleep(3)
        st.rerun()

    except Exception:
        time.sleep(2)
        st.rerun()
            
