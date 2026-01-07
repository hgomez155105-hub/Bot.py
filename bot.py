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

# --- ESTILO (RESTAURADO: SIN NEGRITA ARRIBA, TABLA BLANCA) ---
st.set_page_config(page_title="Scalper Bot", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000; color: #fff; }
    
    /* Números de arriba: LIMPIOS Y SIN NEGRITA */
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-size: 3rem !important; 
        font-weight: 400 !important; 
    }
    
    [data-testid="stMetricLabel"] { 
        color: #FFFFFF !important; 
        font-size: 1.1rem !important; 
    }

    /* TABLA DE ABAJO: BLANCO RESALTADO Y GRUESO */
    .stTable, [data-testid="stTable"], [data-testid="stTable"] td {
        color: #FFFFFF !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }
    
    div[data-testid="metric-container"] { 
        background-color: #111; 
        border: 1px solid #444; 
        border-radius: 10px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN (CORRECCIÓN DE ERROR) ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 1000.0
if 'log' not in st.session_state:
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])
if 'comprado' not in st.session_state:
    st.session_state.comprado = False

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
moneda_nueva = st.sidebar.selectbox("Seleccionar Moneda:", ["SOL", "BTC", "ETH", "ADA", "XRP"])
tp = st.sidebar.slider("Profit %", 0.1, 2.0, 0.8)
sl = st.sidebar.slider("Loss %", 0.1, 5.0, 2.0)

# Botón para limpiar historial si cambias de moneda y quieres empezar de cero
if st.sidebar.button("🗑️ Limpiar Historial"):
    st.session_state.log = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Ganancia $", "Billetera"])
    st.rerun()

# --- FUNCIÓN DE DATOS ---
def traer_datos(symbol):
    try:
        url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
        res = requests.get(url, timeout=5).json()
        p = float(res['USD'])
        rsi_sim = 30 + (p % 40)
        return p, rsi_sim
    except:
        return None, None

# --- PANEL PRINCIPAL ---
st.title(f"🤖 Scalper Bot: {moneda_nueva}")
c1, c2, c3, c4 = st.columns(4)
m_pre = c1.empty()
m_rsi = c2.empty()
m_bil = c3.empty()
m_est = c4.empty()

st.write("---")
cuadro = st.empty()

if st.sidebar.button("🚀 INICIAR OPERACIÓN"):
    while True:
        p, r = traer_datos(moneda_nueva)
        hora = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")
        
        if p:
            evento = "VIGILANDO"
            res_dolar = "$0.00"
            
            # Lógica de simulación
            if not st.session_state.comprado and r < 35:
                st.session_state.comprado = True
                st.session_state.entrada = p
                evento = "🛒 COMPRA"
            elif st.session_state.comprado:
                if p >= st.session_state.entrada * (1+(tp/100)) or p <= st.session_state.entrada * (1-(sl/100)):
                    dif = (p - st.session_state.entrada) * (1000/st.session_state.entrada)
                    st.session_state.saldo += dif
                    res_dolar = f"${dif:.2f}"
                    evento = "💰 VENTA"
                    st.session_state.comprado = False
                else:
                    evento = "⏳ HOLD"

            # Actualizar Interfaz
            m_pre.metric(f"PRECIO {moneda_nueva}", f"${p:,.2f}")
            m_rsi.metric("SENSOR RSI", f"{r:.1f}")
            m_bil.metric("BILLETERA USD", f"${st.session_state.saldo:,.2f}")
            m_est.metric("ESTADO", evento)
            
            # Actualizar Tabla (Forzada en Blanco)
            nuevo = {"Hora": hora, "Evento": evento, "Precio": f"${p:,.2f}", "RSI": f"{r:.1f}", "Ganancia $": res_dolar, "Billetera": f"${st.session_state.saldo:,.2f}"}
            st.session_state.log = pd.concat([pd.DataFrame([nuevo]), st.session_state.log]).head(10)
            st.table(st.session_state.log)
            
            cuadro.success(f"🟢 Operando {moneda_nueva} | {hora} (ARG)")
            time.sleep(10)
            st.rerun()
        else:
            cuadro.warning("🟡 Reconectando señal...")
            time.sleep(5)
