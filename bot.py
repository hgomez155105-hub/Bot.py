import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import ccxt

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="👁️")

# --- CONFIGURACIÓN DE TELEGRAM ---
def enviar_telegram(mensaje, bot_token, chat_id):
    if bot_token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={mensaje}"
            requests.get(url)
        except: pass

# --- CONEXIÓN CON GOOGLE SHEETS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1X6G0T3G0kI6e2o3y3u3u3u3u3u3u3u3u3u3u3u3u3u/export?format=csv" # TU URL DE SHEETS

def verificar_credenciales(usuario_ingresado, clave_ingresada):
    try:
        df_users = pd.read_csv(SHEET_URL)
        user_match = df_users[(df_users['usuario'] == usuario_ingresado) & (df_users['password'].astype(str) == clave_ingresada)]
        return not user_match.empty
    except: return False

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E
    
