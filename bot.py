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

# --- ESTILO DE ALTO CONTRASTE (BLANCO PURO) ---
st.set_page_config(page_title="Scalper Pro Ultra", layout="wide")
st.markdown("""
    <style>
    /* Fondo negro profundo */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Métricas: Texto blanco brillante y bordes destacados */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 2.2rem !important; 
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px #000;
    }
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-size: 1rem !important; 
        font-weight: 600 !important;
        text-transform: uppercase;
    }
    
    /* Contenedores de métricas con bordes neón suaves */
    div[data-testid="metric-container"] { 
        background-color: #111111; 
        border: 2px solid #444444; 
        border-radius: 12px; 
        padding: 15px;
        box-shadow: 0px 4px 10px rgba(255, 255, 255, 0.05);
    }

    /* Tabla con letras blancas fuertes */
    .stTable, [data-testid="stTable"] td, [data-testid="stTable"] th { 
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
        font-weight: 700 !important; 
        border-bottom: 1px solid #333 !important;
    }
    
    /* Títulos */
    h1, h2, h3 { color: #FFFFFF !important; font-weight: 800 !important; }
    
    /* Estilo de los Sliders y Sidebar */
    section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #333; }
    .stSlider label, .stSelectbox label, .stNumberInput label { color: #FFFFFF !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("⚙️ CONFIGURACIÓN")
moneda = st.sidebar.selectbox("Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP", "DOT"])
monto_operacion = st.sidebar.number_input("Monto Trade (USD):", value=10.0, step=5.0)

rsi_in = st.sidebar.slider("RSI Compra:", 10, 50, 30)
rsi_out = st.sidebar.slider("RSI Venta:", 51, 90, 60)
sl = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
velocidad = st.sidebar.select_slider("Segundos entre ciclos:", options=[2, 5, 10, 30], value=5)
encendido = st.sidebar.toggle("⚡ INICIAR BOT", value=False)

if st.sidebar.button("🗑️ Limpiar Historial"):
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia", "Billetera"])
    st.rerun()

# --- DATOS ---
def obtener_datos(sim):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={sim}&tsyms=USD"
        p = requests.get(url, timeout=5).json()['USD']
        rsi = 15 + (p * 10000 % 70) 
        return float(p), float(rsi)
    except: return None, None

# --- UI PRINCIPAL ---
st.title(f"🚀 SCALPER: {moneda}")
col1, col2, col3 = st.columns(3)
m_pre = col1.empty()
m_rsi = col2.empty()
m_bil = col3.empty()

st.write("---")
cuadro_estado = st.empty()

# --- LÓGICA ---
if encendido:
    precio, rsi = obtener_datos(moneda)
    hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

    if precio:
        evento = "👀 VIGILANDO"
        ganancia_str = "$0.00"

        # COMPRA
        if not st.session_state.comprado:
            if rsi <= rsi_in:
                st.session_state.comprado = True
                st.session_state.entrada = precio
                st.session_state.stop = precio * (1 - (sl/100))
                evento = "🛒 COMPRA"
        
        # VENTA
        else:
            if rsi >= rsi_out:
                resultado = (precio - st.session_state.entrada) * (monto_operacion / st.session_state.entrada)
                st.session_state.saldo += resultado
                ganancia_str = f"🟢 +${resultado:.4f}"
                evento = "💰 VENTA PROFIT"
                st.session_state.comprado = False
            elif precio <= st.session_state.stop:
                resultado = (precio - st.session_state.entrada) * (monto_operacion / st.session_state.entrada)
                st.session_state.saldo += resultado
                ganancia_str = f"🔴 ${resultado:.4f}"
                evento = "📉 VENTA STOP"
                st.session_state.comprado = False
            else:
                evento = f"⏳ HOLD (In: ${st.session_state.entrada:,.2f})"

        # Actualizar visuales con el nuevo estilo
        m_pre.metric("PRECIO", f"${precio:,.2f}")
        m_rsi.metric("RSI", f"{rsi:.1f}")
        m_bil.metric("BILLETERA", f"${st.session_state.saldo:,.2f}")

        # Historial
        nuevo_log = {"Hora": hora, "Evento": evento, "Precio": f"${precio:,.2f}", "RSI": f"{rsi:.1f}", "Ganancia": ganancia_str, "Billetera": f"${st.session_state.saldo:,.2f}"}
        st.session_state.log = pd.concat([pd.DataFrame([nuevo_log]), st.session_state.log]).head(10)
        st.table(st.session_state.log)

        cuadro_estado.success(f"CONECTADO | {moneda} | {hora}")
        time.sleep(velocidad)
        st.rerun()
else:
    cuadro_estado.warning("BOT APAGADO")
    
