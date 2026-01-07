import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE SEGURIDAD (CONTRASEÑA) ---
# Cambiá 'caseros2024' por la que vos quieras
PASSWORD_CORRECTA = "caseros2024"

def check_password():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.title("🔐 Acceso Restringido")
        pass_usuario = st.text_input("Ingrese la contraseña para operar:", type="password")
        if st.button("Ingresar"):
            if pass_usuario == PASSWORD_CORRECTA:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
        return False
    return True

# --- 2. HORA ARGENTINA Y ESTILO ---
def hora_arg():
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M:%S")

st.set_page_config(page_title="Scalper Bot Pro - PRIVADO", layout="wide")

# Solo si está autenticado mostramos el bot
if check_password():
    st.markdown("""
        <style>
        .stApp { background-color: #000000; color: #FFFFFF; }
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 2.2rem !important; }
        div[data-testid="metric-container"] { background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 12px; }
        </style>
        """, unsafe_allow_html=True)

    # --- MEMORIA DEL SISTEMA ---
    if 'saldo_billetera' not in st.session_state:
        st.session_state.saldo_billetera = 1000.0
    if 'log_completo' not in st.session_state:
        st.session_state.log_completo = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Resultado $", "Saldo Billetera"])
    if 'comprado' not in st.session_state:
        st.session_state.comprado = False
        st.session_state.precio_entrada = 0.0

    # Botón para cerrar sesión (salir del bot)
    if st.sidebar.button("🔒 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("🤖 Centro de Mando: Simulación Integral")

    # --- PANEL SUPERIOR ---
    c1, c2, c3, c4 = st.columns(4)
    met_precio = c1.empty()
    met_rsi = c2.empty()
    met_billetera = c3.empty()
    met_estado = c4.empty()

    st.write("---")
    cuadro_estado = st.empty()
    tabla_historial = st.empty()

    # --- CONEXIÓN DE DATOS ---
    def obtener_datos():
        try:
            url = "https://min-api.cryptocompare.com/data/price?fsym=SOL&tsyms=USD"
            p = float(requests.get(url, timeout=5).json()['USD'])
            r = 30 + (p % 40) # RSI Simulado
            return p, r
        except: return None, None

    # --- SIDEBAR AJUSTES ---
    st.sidebar.header("⚙️ Estrategia y Riesgo")
    tp_p = st.sidebar.slider("Take Profit %", 0.1, 2.0, 0.8)
    sl_p = st.sidebar.slider("Stop Loss %", 0.1, 5.0, 2.0)
    
    if st.sidebar.button("🔄 Reiniciar Billetera"):
        st.session_state.saldo_billetera = 1000.0
        st.session_state.log_completo = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI", "Resultado $", "Saldo Billetera"])
        st.rerun()

    btn = st.sidebar.button("🚀 INICIAR SIMULACIÓN")

    if btn:
        while True:
            p, r = obtener_datos()
            if p:
                evento = "VIGILANDO"
                res_op = "$0.00"
                
                # LÓGICA DE TRADING
                if not st.session_state.comprado and r < 35:
                    st.session_state.comprado = True
                    st.session_state.precio_entrada = p
                    evento = "🛒 COMPRA"
                elif st.session_state.comprado:
                    target = st.session_state.precio_entrada * (1 + (tp_p/100))
                    stop = st.session_state.precio_entrada
                    
