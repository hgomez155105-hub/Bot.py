import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
import ccxt

# --- CONFIGURACIÓN DE TU SISTEMA ---
# Asegúrate de que esta URL sea la de "Publicar en la web" -> formato CSV
SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA/export?format=csv"
ADMIN_TOKEN = "TU_TELEGRAM_TOKEN"
ADMIN_CHAT_ID = "TU_TELEGRAM_ID"

def verificar_credenciales(u_ingresado, p_ingresado):
    try:
        df = pd.read_csv(SHEET_URL)
        # Limpiamos los nombres de las columnas para que coincidan con tu imagen
        df.columns = df.columns.str.strip().str.lower()
        
        # Buscamos en 'usuario' y 'clave' (tal cual tenés en tu Sheet)
        # Convertimos todo a string para que el '2227' de Admin funcione
        valido = df[(df['usuario'].astype(str).str.strip() == str(u_ingresado).strip()) & 
                    (df['clave'].astype(str).str.strip() == str(p_ingresado).strip())]
        return not valido.empty
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        return False

# --- INTERFAZ Y LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=120)
    st.title("H y G Inovaciones")
    
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    
    if st.button("ACCEDER AL SISTEMA", use_container_width=True):
        if verificar_credenciales(u, p):
            st.session_state.autenticado = True
            st.session_state.user_name = u
            st.rerun()
        else:
            st.error("Credenciales incorrectas. Verifique su base de datos.")
else:
    # --- AQUÍ EMPIEZA TU BOT QUE YA FUNCIONA ---
    st.sidebar.image("https://raw.githubusercontent.com/hgomez155105-hub/Bot.py/main/1000266017.png", width=100)
    st.markdown(f"### 👤 Usuario: {st.session_state.user_name}")
    
    # Resto de la lógica de Malla, Cosecha y Gráficos...
    # (Se mantiene exactamente igual a lo que tenías en las capturas)
    st.success("Sistema Predador en línea")
    
