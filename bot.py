import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- SEGURIDAD ---
PASSWORD = "caseros2024"
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    clave = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if clave == PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# --- ESTILO (Métricas más chicas para que no se corten) ---
st.set_page_config(page_title="Scalper Bot", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    
    /* Números de arriba: REDUCIDOS para visión completa */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 1.8rem !important; 
        font-weight: 400 !important; 
    }
    
    [data-testid="stMetricLabel"] { 
        color: #CCCCCC !important; 
        font-size: 0.9rem !important; 
    }

    /* TABLA: Blanco resaltado */
    .stTable, [data-testid="stTable"] td {
        color: #FFFFFF !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
    }
    
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 1px solid #333; 
        padding: 10px; 
        border-radius: 8px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
moneda_nueva = st.sidebar.selectbox("Seleccionar Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])
tp_p = st.sidebar.slider("Profit %", 0.1, 2.0, 0.8)
sl_p = st.sidebar.slider("Loss %", 0.1, 5.0, 2.0)
encendido = st.sidebar.toggle("🚀 ACTIVAR BOT", value=False)

if st.sidebar.button("🗑️ Limpiar Historial"):
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])
    st.rerun()

# --- DATOS ---
def traer_datos(symbol):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        p = float(res['USD'])
        rsi_sim = 30 + (p % 40)
        return p, rsi_sim
    except: return None, None

# --- PANEL PRINCIPAL ---
st.title(f"🤖 Monitor: {moneda_nueva}")

# Fila 1: Precio y Billetera
c1, c2, c3, c4 = st.columns(4)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()
m_est = c4.empty()

# Fila 2: Precios de Salida (Calculados)
st.write("### Niveles de Salida Estimados")
c5, c6 = st.columns(2)
m_target = c5.empty()
m_stop = c6.empty()

st.write("---")
cuadro = st.empty()

# --- EJECUCIÓN ---
if encendido:
    p, r = traer_datos(moneda_nueva)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
    
    if p:
        # Calcular precios de salida basados en el precio actual
        v_target = p * (1 + (tp_p/100))
        v_stop = p * (1 - (sl_p/100))
        
        evento = "VIGILANDO"
        res_dolar = "$0.00"
        
        if not st.session_state.comprado and r < 35:
            st.session_state.comprado = True
            st.session_state.entrada = p
            evento = "🛒 COMPRA"
        elif st.session_state.comprado:
            # Si ya estamos comprados, usamos el precio de entrada para los niveles
            target_real = st.session_state.entrada * (1 + (tp_p/100))
            stop_real = st.session_state.entrada * (1 - (sl_p/100))
            
            if p >= target_real or p <= stop_real:
                dif = (p - st.session_state.entrada) * (1000/st.session_state.entrada)
                st.session_state.saldo += dif
                res_dolar = f"${dif:.2f}"
                evento = "💰 VENTA"
                st.session_state.comprado = False
            else:
                evento = "⏳ HOLD"

        # Actualizar Métricas Superiores
        m_pre.metric(f"PRECIO {moneda_nueva}", f"${p:,.2f}")
        m_rsi.metric("SENSOR RSI", f"{r:.1f}")
        m_bil.metric("BILLETERA USD", f"${st.session_state.saldo:,.2f}")
        m_est.metric("ESTADO", evento)
        
        # Actualizar Métricas de Niveles (NUEVO)
        m_target.metric("VENDER EN PROFIT (+)", f"${v_target:,.2f}")
        m_stop.metric("SALIR EN STOP (-)", f"${v_stop:,.2f}")
        
        # Tabla
        nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "RSI": f"{r:.1f}", "Ganancia $": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(10)
        st.table(st.session_state.log)
        
        cuadro.success(f"🟢 Activo: {hora} (ARG)")
        time.sleep(10)
        st.rerun()
else:
    cuadro.warning("🔴 Bot Apagado. Use el interruptor lateral.")
    
