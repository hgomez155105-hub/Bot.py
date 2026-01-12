import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Scalper - H y G", layout="wide")

# --- LÓGICA DE CÁLCULO RSI ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios)
    ganancias = deltas.clip(min=0)
    perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:])
    avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- ESTILO VISUAL BINANCE DARK ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .metric-card {
        background: #1E2329; border: 1px solid #474D57;
        border-radius: 12px; padding: 15px; text-align: center;
    }
    .metric-label { font-size: 0.8rem; color: #848E9C; }
    .metric-value { font-size: 1.2rem; font-weight: bold; color: #F0B90B; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    # Pantalla de acceso (puedes volver a poner tu lógica de Google Sheets aquí)
    st.markdown("<h2 style='text-align: center; color: white;'>H y G Inovaciones</h2>", unsafe_allow_html=True)
    if st.button("INGRESAR AL SISTEMA", use_container_width=True):
        st.session_state.autenticado = True
        st.rerun()
else:
    # Inicialización de variables de trading
    if 'ganancia_acumulada' not in st.session_state:
        st.session_state.update({
            'saldo_demo': 1000.0, 'ganancia_acumulada': 0.0, 
            'posiciones': [], 'precios_hist': [], 'ordenes_pendientes': [], 'ultimo_par': ""
        })

    # --- BARRA LATERAL: TODOS LOS CONTROLES MANUALES ---
    with st.sidebar:
        st.title("🛡️ Panel de Usuario")
        
        # 1. ENTORNO MANUAL
        modo = st.radio("MODO DE TRADING:", ["🧪 MODO DEMO", "⚡ MODO REAL"])
        es_real = modo == "⚡ MODO REAL"
        
        st.markdown("---")
        # 2. APIS MANUALES
        st.subheader("🔑 Credenciales API")
        user_api_key = st.text_input("Binance API Key", type="password", placeholder="Pega tu API Key")
        user_api_secret = st.text_input("Binance Secret Key", type="password", placeholder="Pega tu Secret Key")
        
        st.markdown("---")
        # 3. RSI MANUAL (Resguardo)
        st.subheader("📉 Resguardo RSI")
        rsi_manual = st.slider("Cerrar por RSI alto en:", 50, 95, 75, help="Si el RSI toca este nivel y estás en ganancia, el bot cierra para asegurar.")
        
        st.markdown("---")
        # 4. MONEDA Y APALANCAMIENTO MANUAL
        st.subheader("📊 Configuración de Par")
        lista_monedas = ["SOL/USDT", "BTC/USDT", "ETH/USDT", "FET/USDT", "PEPE/USDT", "RNDR/USDT", "SUI/USDT", "NEAR/USDT", "ARB/USDT", "DOGE/USDT"]
        par = st.selectbox("Activo a operar:", lista_monedas)
        
        if par != st.session_state.ultimo_par:
            st.session_state.posiciones = []
            st.session_state.ordenes_pendientes = []
            st.session_state.ultimo_par = par

        val_leverage = st.slider("Apalancamiento Manual (X)", 1, 50, 20)
        
        # 5. NIVELES MANUALES (Malla)
        st.subheader("🕸️ Malla de Compra")
        val_niveles = st.number_input("Cantidad de Niveles", 1, 30, 5)
        val_distancia = st.slider("Distancia entre niveles (%)", 0.1, 10.0, 1.0) / 100
        
        # 6. MONTO Y PROFIT MANUAL
        st.subheader("💰 Gestión de Capital")
        val_monto_total = st.number_input("Inversión Total (USDT)", value=100.0)
        val_profit_manual = st.slider("Profit Global Manual (%)", 0.1, 10.0, 0.5) / 100

    # --- CUERPO PRINCIPAL ---
    st.subheader(f"Ejecutando: {par} en {modo}")
    bot_on = st.toggle("ENCENDER ALGORITMO H y G")

    if bot_on:
        # Validación de seguridad para Real
        if es_real and (not user_api_key or not user_api_secret):
            st.error("⚠️ Error: Faltan las API Keys para operar en Real.")
            st.stop()

        try:
            # Obtener precio real
            coin = par.split('/')[0]
            res = requests.get(f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD").json()
            precio_actual = float(res['USD'])
            
            st.session_state.precios_hist.append(precio_actual)
            if len(st.session_state.precios_hist) > 100: st.session_state.precios_hist.pop(0)
            
            # Cálculo de RSI
            rsi_actual = calcular_rsi(st.session_state.precios_hist)

            # Lógica de Malla (Grid)
            if not st.session_state.posiciones and not st.session_state.ordenes_pendientes:
                monto_por_nivel = val_monto_total / val_niveles
                for n in range(val_niveles):
                    st.session_state.ordenes_pendientes.append({
                        'precio': precio_actual * (1 - (n * val_distancia)),
                        'monto': monto_por_nivel, 'ejecutada': False
                    })

            # Ejecución de órdenes
            for orden in st.session_state.ordenes_pendientes:
                if not orden['ejecutada'] and precio_actual <= orden['precio']:
                    orden['ejecutada'] = True
                    st.session_state.posiciones.append({'entrada': precio_actual, 'monto': orden['monto']})
                    st.toast(f"🛒 Compra en nivel ejecutada: ${precio_actual}")

            # Cierre de operaciones (Profit o RSI)
            if st.session_state.posiciones:
                p_promedio = sum(p['entrada'] for p in st.session_state.posiciones) / len(st.session_state.posiciones)
                target_tp = p_promedio * (1 + val_profit_manual)
                
                # Regla de oro: Siempre en ganancia
                estamos_en_verde = precio_actual > p_promedio
                cierre_por_tp = precio_actual >= target_tp
                cierre_por_rsi = rsi_actual >= rsi_manual and estamos_en_verde

                if cierre_por_tp or cierre_por_rsi:
                    total_invertido = sum(p['monto'] for p in st.session_state.posiciones)
                    pnl_operacion = ((precio_actual - p_promedio) / p_promedio) * val_leverage * total_invertido
                    
                    st.session_state.ganancia_acumulada += pnl_operacion
                    if not es_real: st.session_state.saldo_demo += (total_invertido + pnl_operacion)
                    
                    st.session_state.posiciones = []
                    st.session_state.ordenes_pendientes = []
                    st.balloons()
                    st.success(f"💰 Operación Cerrada | Ganancia: +${pnl_operacion:.2f}")
                    time.sleep(2); st.rerun()

            # --- VISUALIZACIÓN DE MÉTRICAS ---
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"<div class='metric-card'><div class='metric-label'>Precio {coin}</div><div class='metric-value'>${precio_actual:,.4f}</div></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><div class='metric-label'>RSI (14)</div><div class='metric-value'>{rsi_actual:.1f}</div></div>", unsafe_allow_html=True)
            with c3: 
                bal_card = f"${st.session_state.saldo_demo:,.2f}" if not es_real else "⚡ REAL"
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Balance</div><div class='metric-value'>{bal_card}</div></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='metric-card'><div class='metric-label'>PNL Acumulado</div><div class='metric-value' style='color:#00FFAA;'>+${st.session_state.ganancia_acumulada:,.2f}</div></div>", unsafe_allow_html=True)

            # --- GRÁFICO PROFESIONAL ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.precios_hist, mode='lines', line=dict(color='#00FF00', width=2)))
            # Líneas de malla
            for o in st.session_state.ordenes_pendientes:
                color_linea = "white" if not o['ejecutada'] else "#0088FF"
                fig.add_hline(y=o['precio'], line_dash="dot", line_color=color_linea)
            # Línea de TP
            if st.session_state.posiciones:
                fig.add_hline(y=p_promedio * (1 + val_profit_manual), line_dash="dash", line_color="#F0B90B", annotation_text="PROFIT")

            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=0,r=0,t=0,b=0), yaxis=dict(side="right", gridcolor="#23282E"))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            time.sleep(1.5); st.rerun()
        except Exception as e:
            time.sleep(1); st.rerun()
