import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN PRIVADA (Cámbialo aquí y no se borrará) ---
# Pon tu URL de Google Sheets terminada en /export?format=csv
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA/export?format=csv"
# Tus credenciales de Telegram para que el bot te avise a TI
ADMIN_TOKEN = "TU_BOT_TOKEN_AQUI"
ADMIN_CHAT_ID = "TU_CHAT_ID_AQUI"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- FUNCIONES DE SEGURIDAD ---
def enviar_telegram_admin(mensaje):
    """Envía notificaciones solo a tu Telegram personal"""
    if ADMIN_TOKEN != "TU_BOT_TOKEN_AQUI":
        try:
            url = f"https://api.telegram.org/bot{ADMIN_TOKEN}/sendMessage?chat_id={ADMIN_CHAT_ID}&text={mensaje}"
            requests.get(url)
        except: pass

def verificar_credenciales(u, p):
    """Verifica usuario y clave contra la hoja de Google Sheets"""
    try:
        # Forzamos la descarga de los datos actuales
        df_users = pd.read_csv(SHEET_URL)
        # Limpiamos nombres de columnas y datos (quitamos espacios y pasamos a minúsculas)
        df_users.columns = df_users.columns.str.strip().str.lower()
        u_limpio = str(u).strip()
        p_limpio = str(p).strip()
        
        # Buscamos la coincidencia
        match = df_users[(df_users['usuario'].astype(str).str.strip() == u_limpio) & 
                         (df_users['password'].astype(str).str.strip() == p_limpio)]
        return not match.empty
    except Exception as e:
        st.error(f"Error conectando con la base de datos: {e}")
        return False

# --- ESTILO VISUAL H Y G ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    [data-testid="stMetricValue"] { color: #F0B90B !important; font-size: 1.8rem !important; }
    h1, h2, h3, p, label { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

LOGO_URL = "
