import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="☀️")

# --- FUNCIÓN TOP 20 BINANCE ---
def obtener_top_20_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

# --- ESTILOS Y LOGO (SOL DE MAYO) ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# URL del Sol de Mayo
LOGO_SOL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Sol_de_Mayo-Bandera_de_Argentina.svg/1200px-Sol_de_Mayo-Bandera_de_Argentina.svg.png"

# --- SISTEMA DE ACCESO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.image(LOGO_SOL, width=150)
        st.markdown("<h1 style='text-align: center; color: white;'>H y G Inovaciones</h1>", unsafe_allow_html=True)
        user_i = st.text_input("Usuario")
        pass_i = st.text_input("Contraseña", type="password")
        if st.button("ACCEDER AL SISTEMA", use_container_width=True):
            if user_i and pass_i:
                st.session_state.autenticado = True
                st.session_state.user_name = user_i
                st.rerun()
else:
    # --- INICIALIZACIÓN ---
    if 'saldo_demo' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_total': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_malla': [], 
            'ultimo_par': "", 'historial_pnl': []
        })

    # --- HEADER ---
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.markdown(f"## ☀️ H y G Inovaciones - <span class='user-tag'>👤 {st.session_state.user_name}</span>", unsafe_allow_html=True)
    with h_col2:
        st.image(LOGO_SOL, width=60)

    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader("🌐 Mercado")
        par = st.selectbox("Activos en Tendencia:", obtener_top_20_binance())
        
        if par != st.session_state.ultimo_par:
            st.session_state.update({'precios_hist': [], 'posiciones': [], 'ordenes_malla': [], 'ultimo_par': par})
            st.rerun()

        st.divider()
        modo = st.radio("Entorno:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        st.text_input("Binance API Key", type="password")
        st.text_input("Binance Secret Key", type="password")
        
        st.subheader("⚙️ Estrategia de Malla")
        lev = st.slider("Apalancamiento", 1, 50, 20)
        niveles = st.number_input("Cantidad de Órdenes", 1, 20, 5)
        distancia = st.slider("Distancia entre niveles (%)", 0.1, 5.0, 0.5) / 100
        inversion = st.number_input("Inversión Total (USDT)", 10.0, 10000.0, 100.0)
        
        st.subheader("🛡️ Ajuste RSI")
        rsi_compra = st.slider("RSI Compra (Entrada)", 10, 50, 30) # NUEVO SLIDER
        rsi_venta = st.slider("RSI Venta (Salida)", 50, 90, 70)
        tp_global = st.slider("Take Profit (%)", 0.1, 10.0, 1.0) / 100

    # --- EJECUCIÓN ---
    bot_on = st.toggle("ACTIVAR ALGORITMO DE TRADING")

    if bot_on:
        try:
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_act = float(res['USD'])
            st.session_state.precios_hist.append(precio_act)
            if len(st.session_state.precios_hist) > 60: st.session_state.precios_hist.pop(0)
            rsi_val = calcular_rsi(st.session_state.precios_hist)

            # Lógica de Malla Dinámica
            if not st.session_state.ordenes_malla:
                # Solo inicia si el RSI es menor o igual al ajustable
                if rsi_val <= rsi_compra:
                    monto_n = inversion / niveles
                    for i in range(niveles):
                        p_n = precio_act * (1 - (i * distancia))
                        st.session_state.ordenes_malla.append({
                            'id': i+1, 'precio': round(p_n, 4), 'monto': round(monto_n, 2), 'estado': 'PENDIENTE'
                        })

            # Compras y Descuento
            for o in st.session_state.ordenes_malla:
                if o['estado'] == 'PENDIENTE' and precio_act <= o['precio']:
                    if st.session_state.saldo_demo >= o['monto']:
                        st.session_state.saldo_demo -= o['monto']
                        o['estado'] = 'EJECUTADA'
                        st.session_state.posiciones.append({'entrada': precio_act, 'monto': o['monto']})
                        st.toast(f"Nivel {o['id']} comprado")

            # Ventas y Registro
            if st.session_state.posiciones:
                p_prom = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                p_tp = p_prom * (1 + tp_global)
                if precio_act >= p_tp and rsi_val >= rsi_venta:
                    total_inv = sum(p['monto'] for p in st.session_state.posiciones)
                    ganancia = (total_inv * tp_global) * lev
                    st.session_state.historial_pnl.append({
                        'Fecha': datetime.now().strftime("%H:%M"),
                        'Par': par, 'Ganancia': f"+${ganancia:.2f}"
                    })
                    st.session_state.saldo_demo += (total_inv + ganancia)
                    st.session_state.ganancia_total += ganancia
                    st.session_state.update({'posiciones': [], 'ordenes_malla': []})
                    st.balloons(); st.rerun()

            # --- VISUALIZACIÓN ---
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Precio {coin}", f"${precio_act:,.4f}")
            c2.metric("Balance Disponible", f"${st.session_state.saldo_demo:,.2f}")
            c3.metric("PNL Acumulado", f"${st.session_state.ganancia_total:,.2f}", delta=f"RSI: {rsi_val:.1f}")

            # Gráfico Amplio con escala dinámica
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, name="Precio", line=dict(color='#F0B90B', width=3)))
            
            # Dibujar niveles para que el gráfico se expanda
            for o in st.session_state.ordenes_malla:
                color = "green" if o['estado'] == 'EJECUTADA' else "rgba(150,150,150,0.3)"
                fig.add_hline(y=o['precio'], line_dash="dash", line_color=color, annotation_text=f"Nivel {o['id']}")
            
            if st.session_state.posiciones:
                fig.add_hline(y=p_tp, line_color="#00FFFF", line_width=2, annotation_text="Vender Aquí")

            fig.update_layout(height=500, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=10))
            st.plotly_chart(fig, use_container_width=True)

            # Tablas de Control
            col_m, col_h = st.columns(2)
            with col_m:
                st.subheader("📋 Malla Activa")
                st.table(pd.DataFrame(st.session_state.ordenes_malla))
            with col_h:
                st.subheader("📜 Historial de Cierres")
                st.table(pd.DataFrame(st.session_state.historial_pnl))

            time.sleep(1); st.rerun()
        except:
            time.sleep(1); st.rerun()
    
