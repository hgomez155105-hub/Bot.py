import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import base64

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Scalper Bot Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stMetricValue"] { color: #00FF00 !important; font-family: 'Courier New', monospace; }
    div[data-testid="metric-container"] {
        background-color: #111111;
        border: 1px solid #333333;
        padding: 20px;
        border-radius: 15px;
    }
    .stSidebar { background-color: #050505 !important; }
    /* Estilo para la tabla de historial */
    .stDataFrame { background-color: #111; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE SONIDO GRACIOSO/MODERNO ---
def sonar_alerta():
    # Sonido tipo "Coin" de videojuego pero más moderno
    audio_html = """
    <audio autoplay>
      <source src="https://www.myinstants.com/media/sounds/mario-coin.mp3" type="audio/mpeg">
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

st.title("🤖 Centro de Mando: Scalping 0.80%")

# --- TABLERO PRINCIPAL ---
col1, col2, col3 = st.columns(3)
met_precio = col1.empty()
met_rsi = col2.empty()
met_ganancia = col3.empty()

st.write("---")
cuadro_estado = st.empty()

# --- SECCIÓN DE HISTORIAL ---
st.subheader("📜 Historial de Operaciones Recientes")
tabla_historial = st.empty()

# Inicializar historial en la sesión
if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Hora", "Evento", "Precio", "RSI"])

# --- LÓGICA DE CONEXIÓN ---
def obtener_datos_pro(symbol):
    urls = [f"https://api{i}.binance.com/api/v3/ticker/price?symbol={symbol}" for i in range(1, 4)]
    for url in urls:
        try:
            res = requests.get(url, timeout=5).json()
            precio = float(res['price'])
            rsi_fake = 30 + (np.random.random() * 40) # Simulación para ver movimiento
            return precio, rsi_fake
        except: continue
    return None, None

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuración")
par = st.sidebar.text_input("Moneda", value="SOLUSDT").upper()
btn_inicio = st.sidebar.button("🚀 INICIAR VIGILANCIA")

if btn_inicio:
    cuadro_estado.info(f"Conexión establecida. Modo auditivo activado.")
    ganancia_total = 0.0
    
    while True:
        precio, rsi = obtener_datos_pro(par)
        
        if precio:
            met_precio.metric(f"PRECIO {par}", f"${precio:,.2f}")
            met_rsi.metric("SENSOR RSI", f"{rsi:.2f}")
            met_ganancia.metric("GANANCIA TOTAL", f"${ganancia_total:.4f}")
            
            # Lógica de Alerta Auditiva (Si el RSI es bajo)
            if rsi < 35:
                sonar_alerta() # ¡Suena el efecto gracioso!
                nuevo_evento = {"Hora": time.strftime("%H:%M:%S"), "Evento": "Oportunidad Detectada", "Precio": precio, "RSI": rsi}
                st.session_state.historial = pd.concat([pd.DataFrame([nuevo_evento]), st.session_state.historial]).head(10)
                cuadro_estado.warning("🎯 ¡OPORTUNIDAD DETECTADA! (Sonido activado)")
            else:
                cuadro_estado.success(f"🟢 Vigilando {par}...")

            # Actualizar tabla de historial en pantalla
            tabla_historial.dataframe(st.session_state.historial, use_container_width=True)
            
        time.sleep(10)
                
