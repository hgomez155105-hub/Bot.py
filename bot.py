import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="H y G Inovaciones", layout="wide", page_icon="☀️")

def obtener_top_20_binance():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url).json()
        df_vol = pd.DataFrame(res)
        df_vol = df_vol[df_vol['symbol'].str.endswith('USDT')]
        df_vol['quoteVolume'] = df_vol['quoteVolume'].astype(float)
        top_20 = df_vol.sort_values(by='quoteVolume', ascending=False).head(20)
        return [f"{s[:-4]}/USDT" for s in top_20['symbol']]
    except: return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "FET/USDT"]

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    deltas = np.diff(precios); ganancias = deltas.clip(min=0); perdidas = -deltas.clip(max=0)
    avg_gain = np.mean(ganancias[-periodo:]); avg_loss = np.mean(perdidas[-periodo:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / (avg_loss if avg_loss != 0 else 0.001))))

# --- ESTILO ---
st.markdown("""
    <style>
    .stApp { background-color: #0B0E11 !important; }
    .user-tag { background: #1E2329; padding: 5px 15px; border-radius: 20px; border: 1px solid #F0B90B; color: white; }
    </style>
    """, unsafe_allow_html=True)

LOGO_SOL = "
